odoo.define('mail.messaging.component.ChatterTopBarTests', function (require) {
'use strict';

const components = {
    ChatterTopBar: require('mail.messaging.component.ChatterTopbar'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail.messaging.testUtils');

const { makeTestPromise } = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('ChatterTopbar', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createChatterTopbarComponent = async (chatter, otherProps) => {
            const ChatterTopBarComponent = components.ChatterTopBar;
            ChatterTopBarComponent.env = this.env;
            this.component = new ChatterTopBarComponent(
                null,
                Object.assign({ chatterLocalId: chatter.localId }, otherProps)
            );
            await this.component.mount(this.widget.el);
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        delete components.ChatterTopBar.env;
        this.env = undefined;
    },
});

QUnit.test('base rendering', async function (assert) {
    assert.expect(8);

    await this.start();
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonSendMessage`).length,
        1,
        "should have a send message button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonLogNote`).length,
        1,
        "should have a log note button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonScheduleActivity`).length,
        1,
        "should have a schedule activity button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        0,
        "attachments button should not have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_followerListMenu`).length,
        1,
        "should have a follower menu"
    );
});

QUnit.test('base disabled rendering', async function (assert) {
    assert.expect(8);

    await this.start();
    const chatter = this.env.entities.Chatter.create({
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).disabled,
        "send message button should be disabled"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).disabled,
        "log note button should be disabled"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonScheduleActivity`).disabled,
        "schedule activity should be disabled"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonAttachments`).disabled,
        "attachments button should be disabled"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        0,
        "attachments button should not have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelector(`.o_ChatterTopbar_buttonAttachmentsCount`).textContent,
        '0',
        "attachments button counter should be 0"
    );
});

QUnit.test('attachment loading is delayed', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return new Promise(() => {}); // simulate long loading
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        0,
        "attachments button should not have a loader yet"
    );

    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        1,
        "attachments button should now have a loader"
    );
});

QUnit.test('attachment counter while loading attachments', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return new Promise(() => {}); // simulate long loading
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);
    await afterNextRender();

    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        1,
        "attachments button should have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        0,
        "attachments button should not have a counter"
    );
});

QUnit.test('attachment counter transition when attachments become loaded)', async function (assert) {
    assert.expect(7);

    const attachmentPromise = makeTestPromise();
    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                await attachmentPromise;
                return [];
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);
    await afterNextRender();

    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        1,
        "attachments button should have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        0,
        "attachments button should not have a counter"
    );

    attachmentPromise.resolve();
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        0,
        "attachments button should not have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
});

QUnit.test('attachment counter without attachments', async function (assert) {
    assert.expect(4);

    await this.start();
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelector(`.o_ChatterTopbar_buttonAttachmentsCount`).textContent,
        '0',
        'attachment counter should contain "0"'
    );
});

QUnit.test('attachment counter with attachments', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return [{
                    id: 143,
                    filename: 'Blah.txt',
                    mimetype: 'text/plain',
                    name: 'Blah.txt'
                }, {
                    id: 144,
                    filename: 'Blu.txt',
                    mimetype: 'text/plain',
                    name: 'Blu.txt'
                }];
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelector(`.o_ChatterTopbar_buttonAttachmentsCount`).textContent,
        '2',
        'attachment counter should contain "2"'
    );
});

QUnit.test('composer state conserved when clicking on another topbar button', async function (assert) {
    assert.expect(8);

    await this.start();
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar`,
        "should have a chatter topbar"
    );
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonSendMessage`,
        "should have a send message button in chatter menu"
    );
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonLogNote`,
        "should have a log note button in chatter menu"
    );
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonAttachments`,
        "should have an attachments button in chatter menu"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).click();
    });
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonLogNote.o-active`,
        "log button should now be active"
    );
    assert.containsNone(
        document.body,
        `.o_ChatterTopbar_buttonSendMessage.o-active`,
        "send message button should not be active"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_ChatterTopbar_buttonAttachments`).click();
    });
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonLogNote.o-active`,
        "log button should still be active"
    );
    assert.containsNone(
        document.body,
        `.o_ChatterTopbar_buttonSendMessage.o-active`,
        "send message button should still be not active"
    );
});

QUnit.test('rendering with multiple partner followers', async function (assert) {
    assert.expect(7);

    await this.start();
    this.data['res.partner'].records = [{
        id: 100,
        message_follower_ids: [1, 2],
    }];
    this.data['mail.followers'].records = [
        {
            // simulate real return from RPC
            // (the presence of the key and the falsy value need to be handled correctly)
            channel_id: false,
            id: 1,
            name: "Jean Michang",
            partner_id: 12,
        }, {
            // simulate real return from RPC
            // (the presence of the key and the falsy value need to be handled correctly)
            channel_id: false,
            id: 2,
            name: "Eden Hazard",
            partner_id: 11,
        },
    ];
    const chatter = this.env.entities.Chatter.create({
        followerIds: [1, 2],
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "should have followers menu component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_buttonFollowers',
        "should have followers button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should be opened"
    );
    assert.containsN(
        document.body,
        '.o_Follower',
        2,
        "exactly two followers should be listed"
    );
    assert.containsN(
        document.body,
        '.o_Follower_name',
        2,
        "exactly two follower names should be listed"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Follower_name')[0].textContent.trim(),
        "Jean Michang",
        "first follower is 'Jean Michang'"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Follower_name')[1].textContent.trim(),
        "Eden Hazard",
        "second follower is 'Eden Hazard'"
    );
});

QUnit.test('rendering with multiple channel followers', async function (assert) {
    assert.expect(7);

    this.data['res.partner'].records = [{
        id: 100,
        message_follower_ids: [1, 2],
    }];
    await this.start();
    this.data['mail.followers'].records = [
        {
            channel_id: 11,
            id: 1,
            name: "channel numero 5",
            // simulate real return from RPC
            // (the presence of the key and the falsy value need to be handled correctly)
            partner_id: false,
        }, {
            channel_id: 12,
            id: 2,
            name: "channel armstrong",
            // simulate real return from RPC
            // (the presence of the key and the falsy value need to be handled correctly)
            partner_id: false,
        },
    ];
    const chatter = this.env.entities.Chatter.create({
        followerIds: [1, 2],
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "should have followers menu component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_buttonFollowers',
        "should have followers button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should be opened"
    );
    assert.containsN(
        document.body,
        '.o_Follower',
        2,
        "exactly two followers should be listed"
    );
    assert.containsN(
        document.body,
        '.o_Follower_name',
        2,
        "exactly two follower names should be listed"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Follower_name')[0].textContent.trim(),
        "channel numero 5",
        "first follower is 'channel numero 5'"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Follower_name')[1].textContent.trim(),
        "channel armstrong",
        "second follower is 'channel armstrong'"
    );
});

});
});
});

});
