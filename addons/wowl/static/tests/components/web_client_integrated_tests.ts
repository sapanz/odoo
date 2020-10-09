import * as QUnit from "qunit";
import { Component, tags } from "@odoo/owl";
import { Registry } from '../../src/core/registry';
import { ComponentAction, FunctionAction, Service } from '../../src/types';
import { OdooEnv, getFixture, makeFakeMenusService, makeFakeUserService, makeTestEnv, mount, nextTick } from '../helpers';
import { makeMockServer } from '../helpers/mock_server';
import { actionManagerService } from '../../src/services/action_manager/action_manager';
import { WebClient } from '../../src/components/webclient/webclient';

let serverSideActions: any;
let menus: any;
let env: OdooEnv;
let target: HTMLElement;

interface CreateComponentParams {

}
function createComponent(Component: Component, params:CreateComponentParams) {

}

let actionsRegistry: Registry<ComponentAction | FunctionAction>;
let services: Registry<Service>;

class ClientAction extends Component<{}, OdooEnv> {
  static template = tags.xml`<div class="test_client_action">ClientAction</div>`;
}

QUnit.module("ClientAction", {
  async beforeEach() {
    target = getFixture();
    actionsRegistry = new Registry<ComponentAction | FunctionAction>();
    actionsRegistry.add('clientAction', ClientAction);
    services = new Registry<Service>();
    menus = {
      root: { id: "root", children: [1], name: "root" },
      1: { id: 1, children: [], name: "App0" },
    };
    serverSideActions = {
      "wowl.client_action": {
        tag: "clientAction",
        target: "main",
        type: "ir.actions.client",
      },
    };
    services.add("user", makeFakeUserService());
    services.add('menus', makeFakeMenusService(menus));
    makeMockServer(services, { actions: serverSideActions });
    services.add("action_manager", actionManagerService);
    env = await makeTestEnv({ actions: actionsRegistry, services });
  },
});

QUnit.test("can execute client actions from tag name", async function (assert) {
  assert.expect(2);

  const webClient = await mount(WebClient, {env, target});
  env.services.action_manager.doAction('wowl.client_action');
  await nextTick();
  await createWebClient({
    mockRPC: function (route, args) {
      assert.step(args.method || route);
      return this._super.apply(this, arguments);
    },
  });
  assert.strictEqual(
    webClient.el.querySelector(".o_action_manager").innerHTML,
    '<div class="o_action o_client_action_test">Hello World</div>'
  );
  assert.verifySteps([]);

  webClient.destroy();
});
