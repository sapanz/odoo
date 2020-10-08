odoo.define('web.weekly_recurrent_task_tests', function (require) {
    "use strict";
    
    const FormView = require('web.FormView');
    const testUtils = require('web.test_utils');
    let result;
    

    QUnit.module('weekly task', {
        beforeEach() {
            this.data = {
                partner: {
                    fields: {
                        bar: {string: "Bar", type: "boolean"},
                    },
                    records: [
                        { bar: true, },
                    ],
                },
            };
        },
    }, function () {
            QUnit.module('weekly recurrent task widget');

            QUnit.only('simple weekdays widget test', async function (assert) {
                assert.expect(5);
        
                var form = await testUtils.createView({
                    View: FormView,
                    model: 'partner',
                    data: this.data,
                    debug:1,
                    arch: '<form string="Partners">' +
                            '<sheet>' +
                                '<group>' +
                                    '<field name="bar" widget="web_weekly_recurrent_task"/>' +
                                '</group>' +
                            '</sheet>' +
                        '</form>',
                });
                
                function generate_random_number(unwantedNumber){
                    do{
                        result=Math.floor((Math.random() * 6));
                    }while(unwantedNumber.includes(result));
                    return result;
                }
                assert.containsOnce(form, 'i.fa-info-circle');
                await testUtils.dom.click(document.querySelector(".fa-info-circle"));

                let count = 0;
                document.querySelectorAll(".custom-control-input").forEach( item =>{
                    if(item.checked){
                        count += 1;
                    }
                });

                assert.strictEqual(count, 1,"Initially only one checkbox should be checked")

                const today = new Date();
                const unwantedNumber = [today.getDay()];
                const week_day_list = ['su', 'mo', 'tu', 'we', 'th', 'fr', 'sa'];
                 
                let day_number = generate_random_number(unwantedNumber);
                let day = week_day_list[day_number];
                unwantedNumber.push(day_number);                
                
                await testUtils.dom.click(document.getElementById(day));
                assert.strictEqual(document.getElementById(day).checked, true,
                    "check box should be checked");

                await testUtils.dom.click(document.getElementById(day));
                assert.strictEqual(document.getElementById(day).checked, false,
                    "check box should be unchecked");

                day_number = generate_random_number(unwantedNumber);
                day = week_day_list[day_number];
                await testUtils.dom.click(document.getElementById(day));
                
                await testUtils.form.clickSave(form);
                count = 0;
                document.querySelectorAll(".custom-control-input").forEach( item =>{
                    if(item.checked){
                        count += 1;
                    }
                });
                assert.strictEqual(count, 2,"while saving only one checkbox should be checked");

                form.destroy();
            });            
        });
    });
    