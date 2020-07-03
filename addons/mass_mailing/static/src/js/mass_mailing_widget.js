odoo.define('mass_mailing.FieldHtml', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var FieldHtml = require('web_editor.field.html');
var fieldRegistry = require('web.field_registry');

var _t = core._t;


var MassMailingFieldHtml = FieldHtml.extend({
    xmlDependencies: (FieldHtml.prototype.xmlDependencies || []).concat(["/mass_mailing/static/src/xml/mass_mailing.xml"]),
    jsLibs: [
       '/mass_mailing/static/src/js/mass_mailing_snippets.js',
    ],

    custom_events: _.extend({}, FieldHtml.prototype.custom_events, {
        snippets_loaded: '_onSnippetsLoaded',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (!this.nodeOptions.snippets) {
            this.nodeOptions.snippets = 'mass_mailing.email_designer_snippets';
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Commit the change in 'style-inline' on an other field nodeOptions:
     *
     * - inline-field: fieldName to save the html value converted into inline code
     *
     * @override
     */
    commitChanges: async function () {
        var self = this;
        await this._super();
        if (this.mode === 'readonly' || !this.wysiwyg) {
            return;
        }

        const isDirty = this._isDirty;
        const changes = {};
        changes[this.nodeOptions['inline-field']] = this.wysiwyg.getValue('text/mail');

        self.trigger_up('field_changed', {
            dataPointID: self.dataPointID,
            changes: changes,
        });

        if (isDirty && self.mode === 'edit') {
            return self._doAction();
        }
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderEdit: function () {
        if (this.value) {
            this.nodeOptions['style-inline'] = true;
        }
        if (!this.value) {
            this.value = this.recordData[this.nodeOptions['inline-field']];
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    _renderReadonly: function () {
        this.value = this.recordData[this.nodeOptions['inline-field']];
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     * @returns {JQuery}
     */
    _renderTranslateButton: function () {
        var fieldName = this.nodeOptions['inline-field'];
        if (_t.database.multi_lang && this.record.fields[fieldName].translate && this.res_id) {
            return $('<button>', {
                    type: 'button',
                    'class': 'o_field_translate fa fa-globe btn btn-link',
                })
                .on('click', this._onTranslate.bind(this));
        }
        return $();
    },
    /**
     * Swap the previous theme's default images with the new ones.
     * (Redefine the `src` attribute of all images in a $container, depending on the theme parameters.)
     *
     * @private
     * @param {Object} themeParams
     * @param {JQuery} $container
     */
    _switchImages: function (themeParams, $container) {
        if (!themeParams) {
            return;
        }
        $container.find("img").each(function () {
            var $img = $(this);
            var src = $img.attr("src");

            var m = src.match(/^\/web\/image\/\w+\.s_default_image_(?:theme_[a-z]+_)?(.+)$/);
            if (!m) {
                m = src.match(/^\/\w+\/static\/src\/img\/(?:theme_[a-z]+\/)?s_default_image_(.+)\.[a-z]+$/);
            }
            if (!m) {
                return;
            }

            var file = m[1];
            var img_info = themeParams.get_image_info(file);

            if (img_info.format) {
                src = "/" + img_info.module + "/static/src/img/theme_" + themeParams.name + "/s_default_image_" + file + "." + img_info.format;
            } else {
                src = "/web/image/" + img_info.module + ".s_default_image_theme_" + themeParams.name + "_" + file;
            }

            $img.attr("src", src);
        });
    },
    _getContent: async function () {
        return $(this.$('jw-shadow')[0].shadowRoot).find(':not(style,link)');
    },
    /**
     * Add templates & themes.
     *
     * @override
     */
    _getWysiwygOptions: async function () {
        this.needShadow = true;
        const options = await this._super();
        const self = this;

        // Get the snippets to have the templates and themes container.
        const $snippets = $(await this._rpc({
            model: 'ir.ui.view',
            method: 'render_public_asset',
            args: [options.snippets, {}],
            kwargs: {
                context: options.recordInfo.context,
            },
        }));

        // Create templates and themes components.
        const themes = [{
            id: 'default',
            label: _t('Default'),
            render(editor) {
                return editor.getParser().parse('text/html',
                    '<div class="oe_structure"><t-placeholder/></div>');
            },
        }];
        const components = [];
        const templateConfigurations = {};
        $snippets.find("#email_designer_themes").children().each(function () {
            const $template = $(this);
            const data = $template.data();
            const templateId = 'template-' + data.name;
            const themeId = 'theme-' + data.name;
            const nowrap = !!$template.data('nowrap');
            components.push({
                id: templateId,
                async render(editor) {
                    const valueAndTheme = self._getValueAndTheme($template.html());
                    const html = '<t-theme name="' + themeId + '">' + valueAndTheme.value + '</t-theme>';
                    return editor.getParser().parse('text/html', html);
                },
            });
            templateConfigurations[templateId] = {
                componentId: templateId,
                zoneId: 'main',
                label: data.name,
                thumbnail: data.img + '_large.png',
                thumbnailZoneId: 'container',
            };
            themes.push({
                id: themeId,
                label: data.name,
                render(editor) {
                    if (nowrap) {
                        return editor.getParser().parse('text/html',
                        '<div class="o_layout oe_structure" contenteditable="true"><t-placeholder/></div>');
                    } else {
                        // This wrapper structure is the only way to have a responsive
                        // and centered fixed-width content column on all mail clients
                        return editor.getParser().parse('text/html',
                        '<div class="o_layout o_' + data.name + '_theme">' +
                            '<table class="o_mail_wrapper">' +
                                '<tr>' +
                                    '<td class="o_mail_no_resize o_not_editable"></td>' +
                                    '<td class="o_mail_no_options o_mail_wrapper_td oe_structure" contenteditable="true"><t-placeholder/></td>' +
                                    '<td class="o_mail_no_resize o_not_editable"></td>' +
                                '</tr>' +
                            '</table>' +
                        '</div>');
                    }
                },
            });
            // $theme.data("img");

            // const imagesInfo = $theme.data("imagesInfo");
            // _.each(imagesInfo, function (info) {
            //     info = _.defaults(info, imagesInfo.all, {
            //         module: "mass_mailing",
            //         format: "jpg",
            //     });
            // });

            // get_image_info: function (filename) {
            //     if (imagesInfo[filename]) {
            //         return imagesInfo[filename];
            //     }
            //     return imagesInfo.all;
            // }
        });

        // Add the templates and themes as options.
        options.templates = {
            components: components,
            templateConfigurations: templateConfigurations,
        };
        options.themes = themes;

        // Get the current theme.
        const valueAndTheme = this._getValueAndTheme(options.value);
        if (valueAndTheme.themeId) {
            options.value = '<t-theme name="' + valueAndTheme.themeId + '">' + valueAndTheme.value + '</t-theme>';
        } else if (options.value.length) {
            options.value = '<t-theme>' + valueAndTheme.value + '</t-theme>';
        }

        console.log(options);

        return options;
    },
    /**
     * Returns the selected theme, if any.
     *
     * @private
     * @param {string} value
     * @returns {[string, string]} [value, themeId]
     */
    _getValueAndTheme: function (value) {
        const $value = $(value);
        let $layout = $value.hasClass("o_layout") ? $value : $value.find(".o_layout");
        let themeId;
        if ($layout.length) {
            let $contents = $layout.contents();
            const classNameThemeId = [].find.call($layout[0].classList, className => className.includes('_theme'));
            themeId = classNameThemeId && classNameThemeId.slice(2, -6);
            const $td = $contents.find('.o_mail_wrapper_td');
            if ($td.length) {
                $contents = $td.contents();
            } else if ($layout.length) {
                $contents = $layout.contents();
            }
            value = $contents.get().map(node => node.outerHTML || node.textContent).join('');
        }
        return {value: value, themeId: themeId};
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _onSnippetsLoaded: function () {
        this.$el.find("#email_designer_themes").remove();
    },
    /**
     * @override
     * @param {MouseEvent} ev
     */
    _onTranslate: function (ev) {
        this.trigger_up('translate', {
            fieldName: this.nodeOptions['inline-field'],
            id: this.dataPointID,
            isComingFromTranslationAlert: false,
        });
    },
});

fieldRegistry.add('mass_mailing_html', MassMailingFieldHtml);

return MassMailingFieldHtml;

});
