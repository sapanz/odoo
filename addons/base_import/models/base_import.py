# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import collections
import datetime
import io
import itertools
import logging
import operator
import os
import re
import unicodedata

import chardet
import psycopg2
import requests
from PIL import Image

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.tools import (DEFAULT_SERVER_DATE_FORMAT,
                        DEFAULT_SERVER_DATETIME_FORMAT, config, pycompat)
from odoo.tools.func import lazy_property
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.translate import _

FIELDS_RECURSION_LIMIT = 2
ERROR_PREVIEW_BYTES = 200
DEFAULT_IMAGE_TIMEOUT = 3
DEFAULT_IMAGE_MAXBYTES = 10 * 1024 * 1024
DEFAULT_IMAGE_REGEX = r"(?:http|https)://.*(?:png|jpe?g|tiff?|gif|bmp)"
DEFAULT_IMAGE_CHUNK_SIZE = 32768
IMAGE_FIELDS = ["icon", "image", "logo", "picture"]
_logger = logging.getLogger(__name__)

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

try:
    from . import odf_ods_reader
except ImportError:
    odf_ods_reader = None


class File(object):
    extension = None

    def __new__(cls, *args, **kwargs):
        satisfied, req = cls.check_dependency()
        if satisfied:
            return super(File, cls).__new__(cls)
        raise ImportError(_("Unable to load \"{extension}\" file: requires Python module \"{modname}\"").format(extension=cls.extension, modname=req))

    def __init__(self, id, file):
        self.id = id
        self.file = file or b''
        self.table_name = 'temp_csv_%s' % self.id

    @classmethod
    def check_dependency(cls):
        raise NotImplementedError()

    def drop_db(self, cr):
        if tools.table_exists(cr, self.table_name):
            cr.execute("DROP TABLE %s" % self.table_name)

    def reflect_db(self, cr):
        pass

class CSVFile(File):
    extension = 'csv'

    @classmethod
    def check_dependency(cls):
        return True, 'csv'

    @lazy_property
    def csv_data(self):
        if self.encoding != 'utf-8':
            return self.file.decode(self.encoding).encode('utf-8')
        return self.file

    @lazy_property
    def encoding(self):
        return chardet.detect(self.file)['encoding'].lower()

    def get_separator(self, csv_data, quotechar):
        separator = ','
        for candidate in (',', ';', '\t', ' ', '|', unicodedata.lookup('unit separator')):
            # pass through the CSV and check if all rows are the same
            # length & at least 2-wide assume it's the correct one
            it = pycompat.csv_reader(io.BytesIO(csv_data), quotechar=quotechar, delimiter=candidate)
            w = None
            for row in it:
                width = len(row)
                if w is None:
                    w = width
                if width == 1 or width != w:
                    break  # next candidate
            else:  # nobreak
                separator = candidate
                break
        return separator

    def get_options(self):
        # TODO RGA: get quotechar from file
        quotechar = '"'
        separator = self.get_separator(self.csv_data, quotechar)
        return {
           'encoding': self.encoding,
           'separator': separator,
           'quotechar': quotechar,
        }
    def create_temp_table(self, cr, table_name, columns):
        cols = ['{} TEXT,'.format(column) for column in columns]
        query = """
        CREATE TABLE {table} (
            "uid" SERIAL NOT NULL PRIMARY KEY,
            {columns}
        )""".format(table=table_name, columns=" ".join(cols)[:-1])  # [:-1] remove trailing comma
        cr.execute(query)

    def reflect_db(self, cr):
        if not tools.table_exists(cr, self.table_name):
            columns = ['"%s"' % col for col in self.read_header()]
            self.create_temp_table(cr, self.table_name, columns)
            file_stream = io.BytesIO(self.csv_data)
            next(file_stream)   # skip header line
            options = self.get_options()
            cr.copy_from(
                file_stream,
                self.table_name,
                sep=options['separator'],
                columns=columns
            )

    def read_header(self):
        options = self.get_options()
        csv_iterator = pycompat.csv_reader(
            io.BytesIO(self.file),
            quotechar=options['quotechar'],
            delimiter=options['separator'])
        return next(csv_iterator)

    def read(self, cr, header=False):
        assert tools.table_exists(cr, self.table_name), 'File not reflected on temp table'
        cr.execute('SELECT * FROM %s ORDER BY uid ASC' % self.table_name)
        while True:
            # consume result over a series of iterations
            # with each iteration fetching 2000 records
            records = cr.fetchmany(size=2000)
            if not records:
                break
            for row in records:
                yield row[0], [r.strip('\"') for r in row[1:]]

    def write(self, cr, data):
        alias_table = 'csv'

        columns = self.read_header()
        set_query = ",".join(['"%s" = "%s"."%s"' % (col, alias_table, col)  for col in columns])
        alias_query = 'AS "%s"("uid",%s)' % (alias_table, ",".join(['"%s"' % col for col in columns]))
        where = '"%s"."%s" = "%s"."%s"' % (alias_table, 'uid', self.table_name, 'uid')

        rows = [(r['row-id'], *r['row-data']) for r in data]
        placehoder = ",".join(["%s" for r in rows])
        query = """
            UPDATE {table} SET
            {query}
            FROM (VALUES
                {placehoder}
            ) {alias_query}
            WHERE {where}
        """.format(
            table=self.table_name,
            query=set_query,
            placehoder=placehoder,
            alias_query=alias_query,
            where=where
        )
        cr.execute(query, (*rows,))

class XLSDFile(File):
    extension = 'xls'

    @classmethod
    def check_dependency(cls):
        req = 'xlrd'
        try:
            import xlrd
        except ImportError:
            return False, req
        return True, req

    def read_header(self):
        rows = self.read(None, header=True)
        index, header = next(rows)
        return header

    def read(self, cr, header=False):
        book = xlrd.open_workbook(file_contents=self.file or b'')
        rows = self._read_xls_book(book)
        if not header:
            next(rows)
        return rows

    def _read_xls_book(self, book):
        sheet = book.sheet_by_index(0)
        # emulate Sheet.get_rows for pre-0.9.4
        for index, row in enumerate(map(sheet.row, range(sheet.nrows))):
            values = []
            for cell in row:
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        str(cell.value)
                        if is_float
                        else str(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # emulate xldate_as_datetime for pre-0.9.3
                    dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if is_datetime
                        else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u'True' if cell.value else u'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Error cell found while reading XLS/XLSX file: %s") %
                        xlrd.error_text_from_code.get(
                            cell.value, "unknown error code %s" % cell.value)
                    )
                else:
                    values.append(cell.value)
            if any(x for x in values if x.strip()):
                yield index, values

    def write(self, cr, data):
        raise NotImplementedError("TODO: edit XLS/XLSX file")

class XLSXFile(XLSDFile):
    extension = 'xlsx'

    @classmethod
    def check_dependency(cls):
        req = 'xlsx'
        try:
            from xlrd import xlsx
        except ImportError:
            return False, req
        return True, req

class OSDFile(File):
    extension = 'ods'

    @classmethod
    def check_dependency(cls):
        req = 'odfpy'
        try:
            from . import odf_ods_reader
        except ImportError:
            return False, req
        return True, req

    def read_header(self):
        rows = self.read(None, header=True)
        index, header = next(rows)
        return header

    def read(self, cr, header=False):
        rows = self._read_ods()
        if not header:
            next(rows)
        return rows

    def _read_ods(self):
        doc = odf_ods_reader.ODSReader(file=io.BytesIO(self.file or b''))
        for index, row in enumerate(doc.getFirstSheet()):
            if any(x for x in row if x.strip()):
                yield index, row

    def write(self, cr, data):
        raise NotImplementedError("TODO: edit OSD file")


Import_File_Registry = {
    'text/csv': CSVFile,
    'application/vnd.ms-excel': XLSDFile,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': XLSXFile,
    'application/vnd.oasis.opendocument.spreadsheet': OSDFile
}

class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_import_templates(self):
        """
        Get the import templates label and path.

        :return: a list(dict) containing label and template path
                 like ``[{'label': 'foo', 'template': 'path'}]``
        """
        return []

class ImportMapping(models.Model):
    """ mapping of previous column:field selections

    This is useful when repeatedly importing from a third-party
    system: column names generated by the external system may
    not match Odoo's field names or labels. This model is used
    to save the mapping between column names and fields so that
    next time a user imports from the same third-party systems
    we can automatically match the columns to the correct field
    without them having to re-enter the mapping every single
    time.
    """
    _name = 'base_import.mapping'
    _description = 'Base Import Mapping'

    res_model = fields.Char(index=True)
    column_name = fields.Char()
    field_name = fields.Char()


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _can_import_remote_urls(self):
        """ Hook to decide whether the current user is allowed to import
        images via URL (as such an import can DOS a worker). By default,
        allows the administrator group.

        :rtype: bool
        """
        self.ensure_one()
        return self._is_admin()

class Import(models.TransientModel):

    _name = 'base_import.import'
    _description = 'Base Import'

    # allow imports to survive for 12h in case user is slow
    _transient_max_hours = 12.0

    res_model = fields.Char('Model')
    file = fields.Binary('File', help="File to check and/or import, raw binary (not base64)", attachment=False)
    file_name = fields.Char('File Name')
    file_type = fields.Char('File Type')

    @api.model
    def get_fields(self, model, depth=FIELDS_RECURSION_LIMIT):
        """ Recursively get fields for the provided model (through
        fields_get) and filter them according to importability

        The output format is a list of ``Field``, with ``Field``
        defined as:

        .. class:: Field

            .. attribute:: id (str)

                A non-unique identifier for the field, used to compute
                the span of the ``required`` attribute: if multiple
                ``required`` fields have the same id, only one of them
                is necessary.

            .. attribute:: name (str)

                The field's logical (Odoo) name within the scope of
                its parent.

            .. attribute:: string (str)

                The field's human-readable name (``@string``)

            .. attribute:: required (bool)

                Whether the field is marked as required in the
                model. Clients must provide non-empty import values
                for all required fields or the import will error out.

            .. attribute:: fields (list(Field))

                The current field's subfields. The database and
                external identifiers for m2o and m2m fields; a
                filtered and transformed fields_get for o2m fields (to
                a variable depth defined by ``depth``).

                Fields with no sub-fields will have an empty list of
                sub-fields.

        :param str model: name of the model to get fields form
        :param int depth: depth of recursion into o2m fields
        """
        Model = self.env[model]
        importable_fields = [{
            'id': 'id',
            'name': 'id',
            'string': _("External ID"),
            'required': False,
            'fields': [],
            'type': 'id',
        }]
        if not depth:
            return importable_fields

        model_fields = Model.fields_get()
        blacklist = models.MAGIC_COLUMNS + [Model.CONCURRENCY_CHECK_FIELD]
        for name, field in model_fields.items():
            if name in blacklist:
                continue
            # an empty string means the field is deprecated, @deprecated must
            # be absent or False to mean not-deprecated
            if field.get('deprecated', False) is not False:
                continue
            if field.get('readonly'):
                states = field.get('states')
                if not states:
                    continue
                # states = {state: [(attr, value), (attr2, value2)], state2:...}
                if not any(attr == 'readonly' and value is False
                           for attr, value in itertools.chain.from_iterable(states.values())):
                    continue
            field_value = {
                'id': name,
                'name': name,
                'string': field['string'],
                # Y U NO ALWAYS HAS REQUIRED
                'required': bool(field.get('required')),
                'fields': [],
                'type': field['type'],
            }

            if field['type'] in ('many2many', 'many2one'):
                field_value['fields'] = [
                    dict(field_value, name='id', string=_("External ID"), type='id'),
                    dict(field_value, name='.id', string=_("Database ID"), type='id'),
                ]
            elif field['type'] == 'one2many':
                field_value['fields'] = self.get_fields(field['relation'], depth=depth-1)
                if self.user_has_groups('base.group_no_one'):
                    field_value['fields'].append({'id': '.id', 'name': '.id', 'string': _("Database ID"), 'required': False, 'fields': [], 'type': 'id'})

            importable_fields.append(field_value)

        # TODO: cache on model?
        return importable_fields

    @api.model
    def _try_match_column(self, preview_values, options):
        """ Returns the potential field types, based on the preview values, using heuristics
            :param preview_values : list of value for the column to determine
            :param options : parsing options
        """
        values = set(preview_values)
        # If all values are empty in preview than can be any field
        if values == {''}:
            return ['all']

        # If all values starts with __export__ this is probably an id
        if all(v.startswith('__export__') for v in values):
            return ['id', 'many2many', 'many2one', 'one2many']

        # If all values can be cast to int type is either id, float or monetary
        # Exception: if we only have 1 and 0, it can also be a boolean
        if all(v.isdigit() for v in values if v):
            field_type = ['id', 'integer', 'char', 'float', 'monetary', 'many2one', 'many2many', 'one2many']
            if {'0', '1', ''}.issuperset(values):
                field_type.append('boolean')
            return field_type

        # If all values are either True or False, type is boolean
        if all(val.lower() in ('true', 'false', 't', 'f', '') for val in preview_values):
            return ['boolean']

        # If all values can be cast to float, type is either float or monetary
        try:
            thousand_separator = decimal_separator = False
            for val in preview_values:
                val = val.strip()
                if not val:
                    continue
                # value might have the currency symbol left or right from the value
                val = self._remove_currency_symbol(val)
                if val:
                    if options.get('float_thousand_separator') and options.get('float_decimal_separator'):
                        val = val.replace(options['float_thousand_separator'], '').replace(options['float_decimal_separator'], '.')
                    # We are now sure that this is a float, but we still need to find the
                    # thousand and decimal separator
                    else:
                        if val.count('.') > 1:
                            options['float_thousand_separator'] = '.'
                            options['float_decimal_separator'] = ','
                        elif val.count(',') > 1:
                            options['float_thousand_separator'] = ','
                            options['float_decimal_separator'] = '.'
                        elif val.find('.') > val.find(','):
                            thousand_separator = ','
                            decimal_separator = '.'
                        elif val.find(',') > val.find('.'):
                            thousand_separator = '.'
                            decimal_separator = ','
                else:
                    # This is not a float so exit this try
                    float('a')
            if thousand_separator and not options.get('float_decimal_separator'):
                options['float_thousand_separator'] = thousand_separator
                options['float_decimal_separator'] = decimal_separator
            return ['float', 'monetary']
        except ValueError:
            pass

        results = self._try_match_date_time(preview_values, options)
        if results:
            return results

        return ['id', 'text', 'boolean', 'char', 'datetime', 'selection', 'many2one', 'one2many', 'many2many', 'html']


    def _try_match_date_time(self, preview_values, options):
        # Or a date/datetime if it matches the pattern
        date_patterns = [options['date_format']] if options.get(
            'date_format') else []
        date_patterns.extend(DATE_PATTERNS)
        match = check_patterns(date_patterns, preview_values)
        if match:
            options['date_format'] = match
            return ['date', 'datetime']

        datetime_patterns = [options['datetime_format']] if options.get(
            'datetime_format') else []
        datetime_patterns.extend(
            "%s %s" % (d, t)
            for d in date_patterns
            for t in TIME_PATTERNS
        )
        match = check_patterns(datetime_patterns, preview_values)
        if match:
            options['datetime_format'] = match
            return ['datetime']

        return []

    @api.model
    def _find_type_from_preview(self, options, preview):
        type_fields = []
        if preview:
            for column in range(0, len(preview[0])):
                preview_values = [value[column].strip() for value in preview]
                type_field = self._try_match_column(preview_values, options)
                type_fields.append(type_field)
        return type_fields

    def _match_header(self, header, fields, options):
        """ Attempts to match a given header to a field of the
            imported model.

            :param str header: header name from the CSV file
            :param fields:
            :param dict options:
            :returns: an empty list if the header couldn't be matched, or
                      all the fields to traverse
            :rtype: list(Field)
        """
        string_match = None
        IrTranslation = self.env['ir.translation']
        for field in fields:
            # FIXME: should match all translations & original
            # TODO: use string distance (levenshtein? hamming?)
            if header.lower() == field['name'].lower():
                return [field]
            if header.lower() == field['string'].lower():
                # matching string are not reliable way because
                # strings have no unique constraint
                string_match = field
            translated_header = IrTranslation._get_source('ir.model.fields,field_description', 'model', self.env.lang, header).lower()
            if translated_header == field['string'].lower():
                string_match = field
        if string_match:
            # this behavior is only applied if there is no matching field['name']
            return [string_match]

        if '/' not in header:
            return []

        # relational field path
        traversal = []
        subfields = fields
        # Iteratively dive into fields tree
        for section in header.split('/'):
            # Strip section in case spaces are added around '/' for
            # readability of paths
            match = self._match_header(section.strip(), subfields, options)
            # Any match failure, exit
            if not match:
                return []
            # prep subfields for next iteration within match[0]
            field = match[0]
            subfields = field['fields']
            traversal.append(field)
        return traversal

    def _match_headers(self, fields, headers, options):
        """ Attempts to match the imported model's fields to the
            titles of the parsed CSV file, if the file is supposed to have
            headers.

            Will consume the first line of the ``rows`` iterator.

            Returns the list of headers and a dict mapping cell indices
            to key paths in the ``fields`` tree. If headers were not
            requested, both collections are empty.

            :param Iterator rows:
            :param dict fields:
            :param dict options:
            :rtype: (list(str), dict(int: list(str)))
        """
        matches = {}
        mapping_records = self.env['base_import.mapping'].search_read([('res_model', '=', self.res_model)], ['column_name', 'field_name'])
        mapping_fields = {rec['column_name']: rec['field_name'] for rec in mapping_records}
        for index, header in enumerate(headers):
            match_field = []
            mapping_field_name = mapping_fields.get(header.lower())
            if mapping_field_name:
                match_field = mapping_field_name.split('/')
            if not match_field:
                match_field = [field['name'] for field in self._match_header(header, fields, options)]
            matches[index] = match_field or None
        return headers, matches

    @api.multi
    def parse_preview(self, options, count=10):
        """ Generates a preview of the uploaded files, and performs
            fields-matching between the import's file data and the model's
            columns.

            If the headers are not requested (not options.headers),
            ``matches`` and ``headers`` are both ``False``.

            :param int count: number of preview lines to generate
            :param options: format-specific options.
                            CSV: {quoting, separator, headers}
            :type options: {str, str, str, bool}
            :returns: {fields, matches, headers, preview} | {error, preview}
            :rtype: {dict(str: dict(...)), dict(int, list(str)), list(str), list(list(str))} | {str, str}
        """
        self.ensure_one()
        fields = self.get_fields(self.res_model)
        try:
            FileType = self.get_file_type()
            file = FileType(self.id, self.file)
            rows = file.read(self.env.cr)
            headers = file.read_header()
            headers, matches = self._match_headers(fields, headers, options)
            # Match should have consumed the first row (iif headers), get
            # the ``count`` next rows for preview
            preview = [{
                'row-id': uid,
                'row-data': row
            } for uid, row in itertools.islice(rows, count)]
            assert preview, "file seems to have no content"
            header_types = self._find_type_from_preview(options, list(map(lambda line: line['row-data'], preview)))
            if options.get('keep_matches') and len(options.get('fields', [])):
                matches = {}
                for index, match in enumerate(options.get('fields')):
                    if match:
                        matches[index] = match.split('/')

            if options.get('keep_matches'):
                advanced_mode = options.get('advanced')
            else:
                # Check is label contain relational field
                has_relational_header = any(len(models.fix_import_export_id_paths(col)) > 1 for col in headers)
                # Check is matches fields have relational field
                has_relational_match = any(len(match) > 1 for field, match in matches.items() if match)
                advanced_mode = has_relational_header or has_relational_match

            return {
                'fields': fields,
                'matches': matches or False,
                'headers': headers or False,
                'headers_type': header_types or False,
                'preview': preview,
                'options': options,
                'advanced_mode': advanced_mode,
                'debug': self.user_has_groups('base.group_no_one'),
            }
        except Exception as error:
            # Due to lazy generators, UnicodeDecodeError (for
            # instance) may only be raised when serializing the
            # preview to a list in the return.
            _logger.debug("Error during parsing preview", exc_info=True)
            preview = None
            if self.file_type == 'text/csv' and self.file:
                preview = self.file[:ERROR_PREVIEW_BYTES].decode('iso-8859-1')
            return {
                'error': str(error),
                # iso-8859-1 ensures decoding will always succeed,
                # even if it yields non-printable characters. This is
                # in case of UnicodeDecodeError (or csv.Error
                # compounded with UnicodeDecodeError)
                'preview': preview,
            }

    @api.multi
    def set_file(self, file):
        self.ensure_one()
        self.write({
            'file': file.read(),
            'file_name': file.filename,
            'file_type': file.content_type,
        })
        FileType = self.get_file_type()
        file = FileType(self.id, self.file)
        file.reflect_db(self.env.cr)

    def unlink(self):
        for record in self:
            FileType = record.get_file_type()
            file = FileType(record.id, record.file)
            file.drop_db(self.env.cr)

    @api.multi
    def get_file_type(self):
        self.ensure_one()
        mimetype = guess_mimetype(self.file or b'')
        file = None
        for mimetype in [mimetype, self.file_type]:
            file = Import_File_Registry.get(mimetype)
            if file:
                break
        if not file:
            _logger.warn("Failed to load file '%s' (transient id %d) using mimetype", self.file_name or '<unknown>', self.id)

        if self.file_name and not file:
            p, ext = os.path.splitext(self.file_name)
            for file_ext, klass in [(klass.extension, klass) for klass in Import_File_Registry.values()]:
                if file_ext == ext[1:]:
                    file = klass
                    break
        if not file:
            _logger.warn("Failed to load file '%s' (transient id %s) using file extension", self.file_name, self.id)
            raise ValueError(_("Unsupported file format \"{}\", import only supports CSV, ODS, XLS and XLSX").format(self.file_type))
        return file

    @api.model
    def _convert_import_data(self, fields, options):
        """ Extracts the input BaseModel and fields list (with
            ``False``-y placeholders for fields to *not* import) into a
            format Model.import_data can use: a fields list without holes
            and the precisely matching data matrix

            :param list(str|bool): fields
            :returns: (data, fields)
            :rtype: (list(list(str)), list(str))
            :raises ValueError: in case the import data could not be converted
        """
        # Get indices for non-empty fields
        indices = [index for index, field in enumerate(fields) if field]
        if not indices:
            raise ValueError(_("You must configure at least one field to import"))
        # If only one index, itemgetter will return an atom rather
        # than a 1-tuple
        if len(indices) == 1:
            mapper = lambda row: [row[indices[0]]]
        else:
            mapper = operator.itemgetter(*indices)
        # Get only list of actually imported fields
        import_fields = [f for f in fields if f]
        FileType = self.get_file_type()
        file = FileType(self.id, self.file)
        rows_to_import = file.read(self.env.cr)
        data = [
            list(row) for row in map(mapper, [rows for uid, rows in rows_to_import])
            # don't try inserting completely empty rows (e.g. from
            # filtering out o2m fields)
            if any(row)
        ]

        return data, import_fields

    @api.model
    def _remove_currency_symbol(self, value):
        value = value.strip()
        negative = False
        # Careful that some countries use () for negative so replace it by - sign
        if value.startswith('(') and value.endswith(')'):
            value = value[1:-1]
            negative = True
        float_regex = re.compile(r'([+-]?[0-9.,]+)')
        split_value = [g for g in float_regex.split(value) if g]
        if len(split_value) > 2:
            # This is probably not a float
            return False
        if len(split_value) == 1:
            if float_regex.search(split_value[0]) is not None:
                return split_value[0] if not negative else '-' + split_value[0]
            return False
        else:
            # String has been split in 2, locate which index contains the float and which does not
            currency_index = 0
            if float_regex.search(split_value[0]) is not None:
                currency_index = 1
            # Check that currency exists
            currency = self.env['res.currency'].search([('symbol', '=', split_value[currency_index].strip())])
            if len(currency):
                return split_value[(currency_index + 1) % 2] if not negative else '-' + split_value[(currency_index + 1) % 2]
            # Otherwise it is not a float with a currency symbol
            return False

    @api.model
    def _parse_float_from_data(self, data, index, name, options):
        for line in data:
            line[index] = line[index].strip()
            if not line[index]:
                continue
            thousand_separator, decimal_separator = self._infer_separators(line[index], options)
            line[index] = line[index].replace(thousand_separator, '').replace(decimal_separator, '.')
            old_value = line[index]
            line[index] = self._remove_currency_symbol(line[index])
            if line[index] is False:
                raise ValueError(_("Column %s contains incorrect values (value: %s)" % (name, old_value)))

    def _infer_separators(self, value, options):
        """ Try to infer the shape of the separators: if there are two
        different "non-numberic" characters in the number, the
        former/duplicated one would be grouping ("thousands" separator) and
        the latter would be the decimal separator. The decimal separator
        should furthermore be unique.
        """
        # can't use \p{Sc} using re so handroll it
        non_number = [
            # any character
            c for c in value
            # which is not a numeric decoration (() is used for negative
            # by accountants)
            if c not in '()-+'
            # which is not a digit or a currency symbol
            if unicodedata.category(c) not in ('Nd', 'Sc')
        ]

        counts = collections.Counter(non_number)
        # if we have two non-numbers *and* the last one has a count of 1,
        # we probably have grouping & decimal separators
        if len(counts) == 2 and counts[non_number[-1]] == 1:
            return [character for character, _count in counts.most_common()]

        # otherwise get whatever's in the options, or fallback to a default
        thousand_separator = options.get('float_thousand_separator', ' ')
        decimal_separator = options.get('float_decimal_separator', '.')
        return thousand_separator, decimal_separator

    @api.multi
    def _parse_import_data(self, data, import_fields, options):
        """ Lauch first call to _parse_import_data_recursive with an
        empty prefix. _parse_import_data_recursive will be run
        recursively for each relational field.
        """
        return self._parse_import_data_recursive(self.res_model, '', data, import_fields, options)

    @api.multi
    def _parse_import_data_recursive(self, model, prefix, data, import_fields, options):
        # Get fields of type date/datetime
        all_fields = self.env[model].fields_get()
        for name, field in all_fields.items():
            name = prefix + name
            if field['type'] in ('date', 'datetime') and name in import_fields:
                index = import_fields.index(name)
                self._parse_date_from_data(data, index, name, field['type'], options)
            # Check if the field is in import_field and is a relational (followed by /)
            # Also verify that the field name exactly match the import_field at the correct level.
            elif any(name + '/' in import_field and name == import_field.split('/')[prefix.count('/')] for import_field in import_fields):
                # Recursive call with the relational as new model and add the field name to the prefix
                self._parse_import_data_recursive(field['relation'], name + '/', data, import_fields, options)
            elif field['type'] in ('float', 'monetary') and name in import_fields:
                # Parse float, sometimes float values from file have currency symbol or () to denote a negative value
                # We should be able to manage both case
                index = import_fields.index(name)
                self._parse_float_from_data(data, index, name, options)
            elif field['type'] == 'binary' and field.get('attachment') and any(f in name for f in IMAGE_FIELDS) and name in import_fields:
                index = import_fields.index(name)

                with requests.Session() as session:
                    session.stream = True

                    for num, line in enumerate(data):
                        if re.match(config.get("import_image_regex", DEFAULT_IMAGE_REGEX), line[index]):
                            if not self.env.user._can_import_remote_urls():
                                raise AccessError(_("You can not import images via URL, check with your administrator or support for the reason."))

                            line[index] = self._import_image_by_url(line[index], session, name, num)

        return data

    def _parse_date_from_data(self, data, index, name, field_type, options):
        dt = datetime.datetime
        fmt = fields.Date.to_string if field_type == 'date' else fields.Datetime.to_string
        d_fmt = options.get('date_format')
        dt_fmt = options.get('datetime_format')
        for num, line in enumerate(data):
            if not line[index]:
                continue

            v = line[index].strip()
            try:
                # first try parsing as a datetime if it's one
                if dt_fmt and field_type == 'datetime':
                    try:
                        line[index] = fmt(dt.strptime(v, dt_fmt))
                        continue
                    except ValueError:
                        pass
                # otherwise try parsing as a date whether it's a date
                # or datetime
                line[index] = fmt(dt.strptime(v, d_fmt))
            except ValueError as e:
                raise ValueError(_("Column %s contains incorrect values. Error in line %d: %s") % (name, num + 1, e))
            except Exception as e:
                raise ValueError(_("Error Parsing Date [%s:L%d]: %s") % (name, num + 1, e))

    def _import_image_by_url(self, url, session, field, line_number):
        """ Imports an image by URL

        :param str url: the original field value
        :param requests.Session session:
        :param str field: name of the field (for logging/debugging)
        :param int line_number: 0-indexed line number within the imported file (for logging/debugging)
        :return: the replacement value
        :rtype: bytes
        """
        maxsize = int(config.get("import_image_maxbytes", DEFAULT_IMAGE_MAXBYTES))
        try:
            response = session.get(url, timeout=int(config.get("import_image_timeout", DEFAULT_IMAGE_TIMEOUT)))
            response.raise_for_status()

            if response.headers.get('Content-Length') and int(response.headers['Content-Length']) > maxsize:
                raise ValueError(_("File size exceeds configured maximum (%s bytes)") % maxsize)

            content = bytearray()
            for chunk in response.iter_content(DEFAULT_IMAGE_CHUNK_SIZE):
                content += chunk
                if len(content) > maxsize:
                    raise ValueError(_("File size exceeds configured maximum (%s bytes)") % maxsize)

            image = Image.open(io.BytesIO(content))
            w, h = image.size
            if w * h > 42e6:  # Nokia Lumia 1020 photo resolution
                raise ValueError(
                    u"Image size excessive, imported images must be smaller "
                    u"than 42 million pixel")

            return base64.b64encode(content)
        except Exception as e:
            raise ValueError(_("Could not retrieve URL: %(url)s [%(field_name)s: L%(line_number)d]: %(error)s") % {
                'url': url,
                'field_name': field,
                'line_number': line_number + 1,
                'error': e
            })

    @api.multi
    def save_rows(self, rows):
        FileType = self.get_file_type()
        file = FileType(self.id, self.file)
        rows = file.write(self.env.cr, rows)

    @api.multi
    def do(self, fields, columns, options, dryrun=False):
        """ Actual execution of the import

        :param fields: import mapping: maps each column to a field,
                       ``False`` for the columns to ignore
        :type fields: list(str|bool)
        :param columns: columns label
        :type columns: list(str|bool)
        :param dict options:
        :param bool dryrun: performs all import operations (and
                            validations) but rollbacks writes, allows
                            getting as much errors as possible without
                            the risk of clobbering the database.
        :returns: A list of errors. If the list is empty the import
                  executed fully and correctly. If the list is
                  non-empty it contains dicts with 3 keys ``type`` the
                  type of error (``error|warning``); ``message`` the
                  error message associated with the error (a string)
                  and ``record`` the data which failed to import (or
                  ``false`` if that data isn't available or provided)
        :rtype: dict(ids: list(int), messages: list({type, message, record}))
        """
        self.ensure_one()
        self._cr.execute('SAVEPOINT import')

        try:
            data, import_fields = self._convert_import_data(fields, options)
            # Parse date and float field
            data = self._parse_import_data(data, import_fields, options)
        except ValueError as error:
            return {
                'messages': [{
                    'type': 'error',
                    'message': str(error),
                    'record': False,
                }]
            }

        _logger.info('importing %d rows...', len(data))

        name_create_enabled_fields = options.pop('name_create_enabled_fields', {})
        model = self.env[self.res_model].with_context(import_file=True, name_create_enabled_fields=name_create_enabled_fields)
        import_result = model.load(import_fields, data)
        _logger.info('done')

        # If transaction aborted, RELEASE SAVEPOINT is going to raise
        # an InternalError (ROLLBACK should work, maybe). Ignore that.
        # TODO: to handle multiple errors, create savepoint around
        #       write and release it in case of write error (after
        #       adding error to errors array) => can keep on trying to
        #       import stuff, and rollback at the end if there is any
        #       error in the results.
        try:
            if dryrun:
                self._cr.execute('ROLLBACK TO SAVEPOINT import')
                # cancel all changes done to the registry/ormcache
                self.pool.reset_changes()
            else:
                self._cr.execute('RELEASE SAVEPOINT import')
        except psycopg2.InternalError:
            pass

        # Insert/Update mapping columns when import complete successfully
        if import_result['ids'] and options.get('headers'):
            BaseImportMapping = self.env['base_import.mapping']
            for index, column_name in enumerate(columns):
                if column_name:
                    # Update to latest selected field
                    exist_records = BaseImportMapping.search([('res_model', '=', self.res_model), ('column_name', '=', column_name)])
                    if exist_records:
                        exist_records.write({'field_name': fields[index]})
                    else:
                        BaseImportMapping.create({
                            'res_model': self.res_model,
                            'column_name': column_name,
                            'field_name': fields[index]
                        })

        return import_result

_SEPARATORS = [' ', '/', '-', '']
_PATTERN_BASELINE = [
    ('%m', '%d', '%Y'),
    ('%d', '%m', '%Y'),
    ('%Y', '%m', '%d'),
    ('%Y', '%d', '%m'),
]
DATE_FORMATS = []
# take the baseline format and duplicate performing the following
# substitution: long year -> short year, numerical month -> short
# month, numerical month -> long month. Each substitution builds on
# the previous two
for ps in _PATTERN_BASELINE:
    patterns = {ps}
    for s, t in [('%Y', '%y')]:
        patterns.update([ # need listcomp: with genexpr "set changed size during iteration"
            tuple(t if it == s else it for it in f)
            for f in patterns
        ])
    DATE_FORMATS.extend(patterns)
DATE_PATTERNS = [
    sep.join(fmt)
    for sep in _SEPARATORS
    for fmt in DATE_FORMATS
]
TIME_PATTERNS = [
    '%H:%M:%S', '%H:%M', '%H', # 24h
    '%I:%M:%S %p', '%I:%M %p', '%I %p', # 12h
]

def check_patterns(patterns, values):
    for pattern in patterns:
        p = to_re(pattern)
        for val in values:
            if val and not p.match(val):
                break

        else:  # no break, all match
            return pattern

    return None

def to_re(pattern):
    """ cut down version of TimeRE converting strptime patterns to regex
    """
    pattern = re.sub(r'\s+', r'\\s+', pattern)
    pattern = re.sub('%([a-z])', _replacer, pattern, flags=re.IGNORECASE)
    pattern = '^' + pattern + '$'
    return re.compile(pattern, re.IGNORECASE)
def _replacer(m):
    return _P_TO_RE[m.group(1)]

_P_TO_RE = {
    'd': r"(3[0-1]|[1-2]\d|0[1-9]|[1-9]| [1-9])",
    'H': r"(2[0-3]|[0-1]\d|\d)",
    'I': r"(1[0-2]|0[1-9]|[1-9])",
    'm': r"(1[0-2]|0[1-9]|[1-9])",
    'M': r"([0-5]\d|\d)",
    'S': r"(6[0-1]|[0-5]\d|\d)",
    'y': r"(\d\d)",
    'Y': r"(\d\d\d\d)",

    'p': r"(am|pm)",

    '%': '%',
}
