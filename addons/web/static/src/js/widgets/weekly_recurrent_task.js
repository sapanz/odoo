odoo.define('web.weekly_recurrent_task', function (require) {
    'use strict';

    const AbstractField = require('web.AbstractFieldOwl');
    const config = require('web.config');
    const core = require('web.core');
    const fieldRegistry = require('web.field_registry_owl');
    const session = require('web.session');
    const QWeb = core.qweb;


    class RcurrentTaskWidget extends AbstractField {
        constructor(parent) {
            super(...arguments);
            this.parent = parent;
            this.checked_list = {"su":false, "mo":false, "tu":false, "we":false, "th":false, "fr":false, "sa":false};
            this.week_day_list = ['su', 'mo', 'tu', 'we', 'th', 'fr', 'sa'];
        }

        async willStart() {
            if(this.recordData.recurrence_id) {
                const record = await this.env.services.rpc({
                    model: this.recordData.recurrence_id.model,
                    method: 'read',
                    args: [this.recordData.recurrence_id.data.id, this.week_day_list]
                });

                for(let key in record[0]) {
                    if( key != 'id' && record[0][key] == true){
                        this.checked_list[key] = true;
                    }
                }
            }else {
                const today = new Date();
                const weekday = this.week_day_list[today.getDay()];
                this.checked_list[weekday] = true;
            }
        }

        async _renderDropdown() {
            const week_day_default = moment.weekdaysMin();
            let week_days = {}
            for(let i in week_day_default) {
                week_days[week_day_default[i]] = this.week_day_list[i];
            }

            this.el.querySelector('.o_activity').classList.toggle('dropdown-menu-right',config.device.isMobile);
            this.el.querySelector('.o_activity').innerHTML = QWeb.render('web.recurrent_task.Loading');
            this.el.querySelector('.o_activity').innerHTML = QWeb.render('web.RecurrentTask.dropdown.content', {
                selection: self.selection,
                session: session,
                widget: self,
                weekdays: moment.weekdaysMin(true),
                week_days: week_days,
            });

            this._bind_event();



            for(let key in this.checked_list) {
                const check_box = this.el.querySelector('#'+key);
                this.checked_list[key] == true ? check_box.checked = true : check_box.checked = false;
            }
        }

        _bind_event() {
            this.el.querySelectorAll('.custom-control-input').forEach(item => {
                item.addEventListener('click', (item) => {
                    this._onCheckboxClick(item);
                })
            });
        }

        _onDropdownShow() {
            this._renderDropdown();
        }

        _onCheckboxClick(item) {
            this.checked_list[item.toElement.value] = item.toElement.checked;
            this.trigger('field-changed', {
                dataPointID: this.dataPointId,
                changes: this.checked_list,
            });
        }

        willUnmount() {
            for(var key in this.checked_list) {
                this.checked_list[key] = false
            }
        }
    }

    RcurrentTaskWidget.template = ["web.recurrent_task"];
    fieldRegistry.add('web_weekly_recurrent_task', RcurrentTaskWidget);

    return RcurrentTaskWidget;
});
