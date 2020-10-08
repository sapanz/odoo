odoo.define('calendar.CalendarModel', function (require) {
    "use strict";

    const Model = require('web.CalendarModel');

    const CalendarModel = Model.extend({

        /**
         * @override
         * Transform fullcalendar event object to odoo Data object
         */
        calendarEventToRecord(event) {
            const data = this._super(event);
            return _.extend({}, data, {
                'recurrence_update': event.recurrenceUpdate,
            });
        },
        /**
         * Split the events to display an event for each attendee with the correct status if the "all"
         * filter has not been enabled.
         * @override
         */
        async _calendarEventByAttendee(events) {
            var self = this;
            var data = await this._super(...arguments);
            let allFilter = self.loadParams.filters.partner_ids && _.find(self.loadParams.filters.partner_ids.filters, f => f.value === "all") || false;
            let attendees = await self._rpc({
                model: 'calendar.attendee',
                method: 'search_read',
                domain: [['event_id', 'in', _.map(events, event => event.id)]],
            });
            if (allFilter && !allFilter.active) {
                _.each(events, function (event) {
                    _.each(event.record.partner_ids, function (attendee) {
                        if (_.find(self.loadParams.filters.partner_ids.filters, f => f.active && f.value == attendee)) {
                            let e = JSON.parse(JSON.stringify(event));
                            e.attendee_id = attendee;
                            let status = _.find(attendees, a => a.partner_id[0] == attendee && a.event_id[0] == e.record.id);
                            if (status) {
                                e.record.attendee_status = status.state;
                            }
                            
                            data.push(e);
                        }
                    });
                });
            }
            data = data.length ? data : self.data.data;
            _.each(data, function (event) {
                let allAttendeesStatus = _.map(
                    _.filter(
                        attendees, a => a.event_id[0] === event.record.id && a.partner_id[0] !== event.record.partner_id[0]
                    ), a => a.state);
                let alone = !_.find(allAttendeesStatus, a => a !== 'declined');
                event.record.alone = (event.attendee_id && event.attendee_id === event.record.partner_id[0] || allFilter && allFilter.active) &&
                                        event.record.partner_ids.length > 1 && event.record.partner_id[0] === self.getSession().partner_id && alone;
            });
            return data;
        },
    });

    return CalendarModel;
});
