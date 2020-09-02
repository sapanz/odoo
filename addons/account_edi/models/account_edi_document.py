# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from psycopg2 import OperationalError
import logging

_logger = logging.getLogger(__name__)


class AccountEdiDocument(models.Model):
    _name = 'account.edi.document'
    _description = 'Electronic Document for an account.move'

    # == Stored fields ==
    move_id = fields.Many2one('account.move')
    edi_format_id = fields.Many2one('account.edi.format')
    attachment_id = fields.Many2one('ir.attachment', help='The file generated by edi_format_id when the invoice is posted (and this document is processed).')
    state = fields.Selection([('to_send', 'To Send'), ('sent', 'Sent'), ('to_cancel', 'To Cancel'), ('cancelled', 'Cancelled')])
    error = fields.Html()
    error_level = fields.Selection(selection=[('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')])

    # == Not stored fields ==
    name = fields.Char(related='attachment_id.name')
    edi_format_name = fields.Char(string='Format Name', related='edi_format_id.name')

    _sql_constraints = [
        (
            'unique_edi_document_by_move_by_format',
            'UNIQUE(edi_format_id, move_id)',
            'Only one edi document by move by format',
        ),
    ]

    def _prepare_jobs(self):
        """Creates a list of jobs to be performed by '_process_jobs' for the documents in self.
        Each document represent a job, BUT if multiple documents have the same state, edi_format_id,
        doc_type (invoice or payment) and company_id AND the edi_format_id supports batching, they are grouped
        into a single job.

        :returns:         A list of tuples (key, documents)
        * key:            A tuple (edi_format_id, state, doc_type, company_id)
        ** edi_format_id: The format to perform the operation with
        ** state:         The state of the documents of this job
        ** doc_type:      Are the moves of this job invoice or payments ?
        ** company_id:    The company the moves belong to
        * documents:      The documents related to this job. If edi_format_id does not support batch, length must be one
        """

        to_process = []
        batches = {}
        for edi_doc in self.filtered(lambda d: d.state in ('to_send', 'to_cancel') and d.error_level != 'error'):
            move = edi_doc.move_id
            edi_format = edi_doc.edi_format_id
            if move.is_invoice(include_receipts=True):
                doc_type = 'invoice'
            elif move.payment_id or move.statement_line_id:
                doc_type = 'payment'
            else:
                continue

            key = (edi_format, edi_doc.state, doc_type, move.company_id)
            if edi_format._support_batching():
                if not batches.get(key, None):
                    batches[key] = self.env['account.edi.document']
                batches[key] |= edi_doc
            else:
                to_process.append((key, edi_doc))
        to_process.extend(batches.items())
        return to_process

    @api.model
    def _process_jobs(self, to_process):
        """Post or cancel move_id (invoice or payment) by calling the related methods on edi_format_id.
        Invoices are processed before payments.
        """
        def _postprocess_post_edi_results(documents, edi_result):
            attachments_to_unlink = self.env['ir.attachment']
            for document in documents:
                move = document.move_id
                move_result = edi_result.get(move, {})
                if move_result.get('attachment'):
                    old_attachment = document.attachment_id
                    document.write({
                        'attachment_id': move_result['attachment'].id,
                        'state': 'sent',
                        'error': False,
                        'error_level': False,
                    })
                    if not old_attachment.res_model or not old_attachment.res_id:
                        attachments_to_unlink |= old_attachment
                else:
                    document.error = move_result.get('error', False)
                    document.error_level = move_result.get('error_level', 'error') if document.error else False

            # Attachments that are not explicitly linked to a business model could be removed because they are not
            # supposed to have any traceability from the user.
            attachments_to_unlink.unlink()

        def _postprocess_cancel_edi_results(documents, edi_result):
            invoice_ids_to_cancel = set()  # Avoid duplicates
            attachments_to_unlink = self.env['ir.attachment']
            for document in documents:
                move = document.move_id
                move_result = edi_result.get(move, {})
                if move_result.get('success'):
                    old_attachment = document.attachment_id
                    document.write({
                        'state': 'cancelled',
                        'error': False,
                        'attachment_id': False,
                        'error_level': False,
                    })

                    if move.is_invoice(include_receipts=True) and move.state == 'posted':
                        # The user requested a cancellation of the EDI and it has been approved. Then, the invoice
                        # can be safely cancelled.
                        invoice_ids_to_cancel.add(move.id)

                    if not old_attachment.res_model or not old_attachment.res_id:
                        attachments_to_unlink |= old_attachment

                else:
                    document.error = move_result.get('error', False)
                    document.error_level = move_result.get('error_level', 'error') if document.error else False

            if invoice_ids_to_cancel:
                invoices = self.env['account.move'].browse(list(invoice_ids_to_cancel))
                invoices.button_draft()
                invoices.button_cancel()

            # Attachments that are not explicitly linked to a business model could be removed because they are not
            # supposed to have any traceability from the user.
            attachments_to_unlink.unlink()

        test_mode = self._context.get('edi_test_mode', False)

        # ==== Process invoices ====
        payments = []
        for key, batches in to_process:
            edi_format, state, doc_type, company_id = key
            if doc_type == 'payment':
                payments.append((key, batches))
                continue  # payments are processed after invoices

            for documents in batches:
                try:
                    with self.env.cr.savepoint():
                        # Locks the documents in DB. Avoid sending an invoice twice (the documents can be processed by the CRON but also manually).
                        self._cr.execute('SELECT * FROM account_edi_document WHERE id IN %s FOR UPDATE NOWAIT', [tuple(self.ids)])

                        if state == 'to_send':
                            edi_result = edi_format._post_invoice_edi(documents.move_id, test_mode=test_mode)
                            _postprocess_post_edi_results(documents, edi_result)
                        elif state == 'to_cancel':
                            edi_result = edi_format._cancel_invoice_edi(documents.move_id, test_mode=test_mode)
                            _postprocess_cancel_edi_results(documents, edi_result)

                except OperationalError as e:
                    if e.pgcode == '55P03':
                        _logger.debug('Another transaction already locked documents rows. Cannot process documents.')
                    else:
                        raise e

        # ==== Process payments ====
        for key, batches in payments:
            edi_format, state, doc_type, company_id = key

            for documents in batches:
                try:
                    with self.env.cr.savepoint():
                        self._cr.execute('SELECT * FROM account_edi_document WHERE id IN %s FOR UPDATE NOWAIT', [tuple(self.ids)])

                        if state == 'to_send':
                            edi_result = edi_format._post_payment_edi(documents.move_id, test_mode=test_mode)
                            _postprocess_post_edi_results(documents, edi_result)
                        elif state == 'to_cancel':
                            edi_result = edi_format._cancel_payment_edi(documents.move_id, test_mode=test_mode)
                            _postprocess_cancel_edi_results(documents, edi_result)

                except OperationalError as e:
                    if e.pgcode == '55P03':
                        _logger.debug('Another transaction already locked documents rows. Cannot process documents.')
                    else:
                        raise e

    def _process_documents_no_web_services(self):
        """ Post and cancel all the documents that don't need a web service.
        """
        jobs = self.filtered(lambda d: not d.edi_format_id._needs_web_services())._prepare_jobs()
        self._process_jobs(jobs)

    def _process_documents_web_services(self, job_count=None):
        """ Post and cancel all the documents that need a web service. This is called by CRON.

        :param job_count: Limit to the number of jobs to process among the ones that are available for treatment.
        """
        jobs = self.filtered(lambda d: d.edi_format_id._needs_web_services())._prepare_jobs()
        self._process_jobs(jobs[0:job_count or len(jobs)])
