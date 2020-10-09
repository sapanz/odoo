import { Menu, MenuData, MenuService, MenuTree } from "../../src/services/menus";
import { UserService } from "../../src/services/user";
import { Odoo, OdooEnv, OdooConfig, Service } from "../../src/types";
import { RPC } from "../../src/services/rpc";
import type { Deferred } from "./utility";

// // -----------------------------------------------------------------------------
// // Mock Services
// // -----------------------------------------------------------------------------

/**
 * Simulate a fake user service.  For convenience, by default, this fake user
 * service will return { uid: 2 } as context, even though it is not a valid
 * context.  If this is significant for a test, then the `fullContext` option
 * should be set to true.
 */
export function makeFakeUserService(
  values?: Partial<UserService>,
  fullContext: boolean = false
): Service<UserService> {
  const odoo = makeTestOdoo();
  const { uid, name, username, is_admin, user_companies, partner_id } = odoo.session_info;
  const { user_context } = odoo.session_info;
  return {
    name: "user",
    deploy(env: OdooEnv, config: OdooConfig): UserService {
      const { localization } = config;
      const context = fullContext ? user_context : ({ uid: 2 } as any);
      const result = {
        dateFormat: localization.dateFormat,
        decimalPoint: localization.decimalPoint,
        direction: localization.direction,
        grouping: localization.grouping,
        multiLang: localization.multiLang,
        thousandsSep: localization.thousandsSep,
        timeFormat: localization.timeFormat,
        context,
        userId: uid,
        name: name,
        userName: username,
        isAdmin: is_admin,
        partnerId: partner_id,
        allowed_companies: user_companies.allowed_companies,
        current_company: user_companies.current_company,
        lang: user_context.lang,
        tz: "Europe/Brussels",
      };
      Object.assign(result, values);
      return result;
    },
  };
}

export function makeFakeMenusService(menuData?: MenuData): Service<MenuService> {
  const _menuData = menuData || {
    root: { id: "root", children: [1], name: "root" },
    1: { id: 1, children: [], name: "App0" },
  };
  return {
    name: "menus",
    deploy() {
      const menusService = {
        getMenu(menuId: keyof MenuData) {
          return _menuData![menuId];
        },
        getApps() {
          return this.getMenu("root").children.map((mid) => this.getMenu(mid));
        },
        getAll() {
          return Object.values(_menuData);
        },
        getMenuAsTree(menuId: keyof MenuData) {
          const menu = this.getMenu(menuId) as MenuTree;
          if (!menu.childrenTree) {
            menu.childrenTree = menu.children.map((mid: Menu["id"]) => this.getMenuAsTree(mid));
          }
          return menu;
        },
      };
      return menusService;
    },
  };
}

type MockedRoute = (params: Parameters<RPC>[1]) => any;
export interface MockedRoutes {
  [route: string]: MockedRoute;
}
export const standardMockedRoutes: MockedRoutes = {};
export function makeFakeRPCService(mockedRoutes?: MockedRoutes): Service<RPC> {
  return {
    name: "rpc",
    deploy() {
      return async (...args: Parameters<RPC>) => {
        const [route, routeArgs] = args;
        let res;
        if (mockedRoutes && route in mockedRoutes) {
          res = mockedRoutes[route](routeArgs);
        }
        if (res === undefined && route in standardMockedRoutes) {
          res = standardMockedRoutes[route](routeArgs);
        }
        return res;
      };
    },
  };
}

export function makeTestOdoo(): Odoo {
  return {
    session_info: {
      cache_hashes: {
        load_menus: "161803",
        translations: "314159",
      },
      user_context: {
        lang: "en",
        uid: 7,
        tz: "taht",
      },
      qweb: "owl",
      uid: 7,
      name: "Mitchell",
      username: "The wise",
      is_admin: true,
      partner_id: 7,
      user_companies: {
        allowed_companies: [[1, "Hermit"]],
        current_company: [1, "Hermit"],
      },
      db: "test",
      server_version: "1.0",
      server_version_info: ["1.0"],
    },
  };
}

export function makeMockXHR(
  response?: any,
  sendCb?: (data: any) => void,
  def?: Deferred<any>
): typeof XMLHttpRequest {
  let MockXHR: typeof XMLHttpRequest = function () {
    return {
      _loadListener: null,
      url: "",
      addEventListener(type: string, listener: any) {
        if (type === "load") {
          this._loadListener = listener;
        }
      },
      open(method: string, url: string) {
        this.url = url;
      },
      setRequestHeader() {},
      async send(data: string) {
        if (sendCb) {
          sendCb.call(this, JSON.parse(data));
        }
        if (def) {
          await def;
        }
        (this._loadListener as any)();
      },
      response: JSON.stringify(response || ""),
    };
  } as any;
  return MockXHR;
}

//   // -----------------------------------------------------------------------------
//   // Low level API mocking
//   // -----------------------------------------------------------------------------

type MockFetchFn = (route: string) => any;

interface MockFetchParams {
  mockFetch?: MockFetchFn;
}

export function makeMockFetch(params: MockFetchParams): typeof fetch {
  const mockFetch: MockFetchFn = (route) => {
    if (route.includes("load_menus")) {
      return {};
    }
    return "";
  };
  const fetch: MockFetchFn = (...args) => {
    let res = params && params.mockFetch ? params.mockFetch(...args) : undefined;
    if (res === undefined || res === null) {
      res = mockFetch(...args);
    }
    return Array.isArray(res) ? res : [res];
  };
  return (input: RequestInfo) => {
    const route = typeof input === "string" ? input : input.url;
    const res = fetch(route);
    const blob = new Blob(
      res.map((r: any) => JSON.stringify(r)),
      { type: "application/json" }
    );
    return Promise.resolve(new Response(blob, { status: 200 }));
  };
}
