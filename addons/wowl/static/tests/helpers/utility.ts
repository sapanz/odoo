import { Component } from "@odoo/owl";
import { getDefaultLocalization } from "../../src/core/localization";
import { Registry } from "../../src/core/registry";
import { makeEnv } from "../../src/env";
import { Odoo, OdooConfig, OdooEnv, Type } from "../../src/types";
import { makeTestOdoo } from "./mocks";

// export { OdooEnv } from "../../src/types";

// -----------------------------------------------------------------------------
// Main Helpers
// -----------------------------------------------------------------------------
interface MountParameters {
  env: OdooEnv;
  target: HTMLElement;
}

export async function mount<T extends Type<Component>>(
  C: T,
  params: MountParameters
): Promise<InstanceType<T>> {
  ((C as any) as typeof Component).env = params.env;
  const component: Component = new C(null);
  await component.mount(params.target, { position: "first-child" });
  return component as any;
}

export type TestConfig = Partial<
  {
    [K in keyof OdooConfig]: OdooConfig[K] extends Registry<any>
      ? OdooConfig[K]
      : Partial<OdooConfig[K]>;
  }
>;

export function makeTestConfig(config: TestConfig = {}): OdooConfig {
  const browser = (config.browser || {}) as OdooConfig["browser"];
  const localization = config.localization || (getDefaultLocalization() as any);
  const odoo: Odoo = makeTestOdoo();
  const _t = config._t || (((str: string) => str) as any);
  return {
    browser,
    localization,
    _t,
    templates,
    services: config.services || new Registry(),
    Components: config.Components || new Registry(),
    actions: config.actions || new Registry(),
    systray: config.systray || new Registry(),
    views: new Registry(),
    odoo,
  };
}

export async function makeTestEnv(config: TestConfig = {}): Promise<OdooEnv> {
  return await makeEnv(makeTestConfig(config));
}

export function getFixture(): HTMLElement {
  if (QUnit.config.debug) {
    return document.body;
  } else {
    return document.querySelector("#qunit-fixture") as HTMLElement;
  }
}

export async function nextTick(): Promise<void> {
  await new Promise((resolve) => window.requestAnimationFrame(resolve));
  await new Promise((resolve) => setTimeout(resolve));
}

export interface Deferred<T> extends Promise<T> {
  resolve: (value?: T) => void;
}

export function makeDeferred<T>(): Deferred<T> {
  let resolve;
  let prom = new Promise((_r) => {
    resolve = _r;
  }) as Deferred<T>;
  prom.resolve = resolve as any;
  return prom;
}

export function click(el: HTMLElement, selector?: string) {
  let target = el;
  if (selector) {
    const els = el.querySelectorAll<HTMLElement>(selector);
    if (els.length === 0) {
      throw new Error(`Found no element to click on (selector: ${selector})`);
    }
    if (els.length > 1) {
      throw new Error(
        `Found ${els.length} elements to click on, instead of 1 (selector: ${selector})`
      );
    }
    target = els[0];
  }
  const ev = new MouseEvent("click");
  target.dispatchEvent(ev);
  return nextTick();
}

// -----------------------------------------------------------------------------
// Private (should not be called from any test)
// -----------------------------------------------------------------------------
let templates: string;

export function setTemplates(xml: string) {
  templates = xml;
}
