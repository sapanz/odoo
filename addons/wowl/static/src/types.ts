import type { Component } from "@odoo/owl";
import { Env } from "@odoo/owl/dist/types/component/component";
import { EventBus } from "@odoo/owl/dist/types/core/event_bus";
import { Localization } from "./core/localization";
import type { Registry } from "./core/registry";
import type { actionManagerService } from "./services/action_manager/action_manager";
import type { crashManagerService } from "./services/crash_manager";
import type { menusService } from "./services/menus";
import { DBRecord, modelService } from "./services/model";
import type { notificationService } from "./services/notifications";
import { routerService } from "./services/router";
// add here each service type to have better typing for useService
import type { rpcService } from "./services/rpc";
import type { userService } from "./services/user";
import { viewManagerService } from "./services/view_manager";

// import type { ComponentAction, FunctionAction } from "./services/action_manager/helpers";

interface CacheHashes {
  load_menus: string;
  translations: string;
}

interface UserContext {
  lang: string;
  tz: string;
  uid: number;
}

export type UserCompany = [number, string];

interface UserCompanies {
  allowed_companies: UserCompany[];
  current_company: UserCompany;
}

export interface SessionInfo {
  cache_hashes: CacheHashes;
  user_context: UserContext;
  qweb: string;
  uid: number;
  name: string;
  username: string;
  is_admin: boolean;
  partner_id: number;
  user_companies: UserCompanies;
  db: string;
  server_version: string;
  server_version_info: (number | string)[];
}

export interface Odoo {
  session_info: SessionInfo;
}

interface DBInfo {
  db: string;
  server_version: string;
  server_version_info: (number | string)[];
}

interface Debug {
  root: Component;
}

export interface RuntimeOdoo {
  __DEBUG__: Debug;
  info: DBInfo;
}

export interface Type<T> extends Function {
  new (...args: any[]): T;
}

export interface Service<T = any> {
  name: string;
  dependencies?: string[];
  deploy: (env: OdooEnv, config: OdooConfig) => Promise<T> | T;
}

type Browser = Env["browser"];

export interface OdooBrowser extends Browser {
  XMLHttpRequest: typeof window["XMLHttpRequest"];
  console: typeof window["console"];
}

export interface OdooEnv extends Env {
  browser: OdooBrowser;
  services: Services;
  registries: Registries;
  bus: EventBus;
  _t: (str: string) => string;
}

export type ComponentAction = Type<Component<{}, OdooEnv>>;
export type FunctionAction = () => void;

interface Registries {
  Components: Registry<Type<Component>>;
  services: Registry<Service<any>>;
  actions: Registry<ComponentAction | FunctionAction>;
  views: Registry<View>;
  systray: Registry<SystrayItem>;
}

export interface OdooConfig extends Registries {
  browser: OdooBrowser;
  localization: Localization;
  odoo: Odoo;
  templates: string;
  _t: (str: string) => string;
}

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------
type Unwrap<T> = T extends Promise<infer U> ? U : T;
type Nullify<T> = T extends void ? null : T;
type ServiceType<T extends (...args: any[]) => any> = Nullify<Unwrap<ReturnType<T>>>;

export interface Services {
  action_manager: ServiceType<typeof actionManagerService["deploy"]>;
  crash_manager: ServiceType<typeof crashManagerService["deploy"]>;
  menus: ServiceType<typeof menusService["deploy"]>;
  model: ServiceType<typeof modelService["deploy"]>;
  notifications: ServiceType<typeof notificationService["deploy"]>;
  rpc: ServiceType<typeof rpcService["deploy"]>;
  router: ServiceType<typeof routerService["deploy"]>;
  user: ServiceType<typeof userService["deploy"]>;
  view_manager: ServiceType<typeof viewManagerService["deploy"]>;

  [key: string]: any;
}

export type ViewType =
  | "list"
  | "form"
  | "kanban"
  | "calendar"
  | "pivot"
  | "graph"
  | "activity"
  | "grid"
  | string;

export interface View {
  name: string;
  icon: string;
  multiRecord: boolean;
  type: ViewType;
  Component: Type<Component<{}, OdooEnv>>;
}

export interface SystrayItem {
  name: string;
  Component: Type<Component>;
  sequence?: number;
}

/*
 *  MODELS AND FIELDS DEFINITION
 */

export type FieldType = "char" | "one2many" | "many2many" | "number";

export interface FieldDefinition {
  relation?: string;
  relation_field?: string;
  string: string;
  type: FieldType;
}

export interface ModelFields {
  id: FieldDefinition;
  [fieldName: string]: FieldDefinition;
}
export interface ModelData {
  defaults?: keyof ModelFields;
  fields: ModelFields;
  records: DBRecord[];
  methods?: ModelMethods;
}
type Method = (args: any[], kwargs: any) => any;
export interface ModelMethods {
  [methodName: string]: Method;
}
