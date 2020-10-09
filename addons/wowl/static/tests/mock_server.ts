import { Component } from "@odoo/owl";
import { OdooEnv, Service } from '../src/types';
import { Model, ModelBuilder , DBRecord } from '../src/services/model';
import { Action } from '../src/services/action_manager/helpers';

// Aims:
// - Mock service model high level
// - propose mock model.call lower level
// - propose mock RPC low level

// Can be passed data
// returns at least model service

type FieldType =
  | "char"
  | "one2many"
  | "many2many"
  | "number"
;

interface FieldDefiniton {
  relation?: string,
  relation_field?: string,
  string: string,
  type: FieldType,
}

interface ModelFields {
  id: FieldDefiniton,
  [fieldName: string]: FieldDefiniton,
}
interface ModelData {
  defaults?: keyof ModelFields, 
  fields: ModelFields,
  records: DBRecord[],
}
type ModelMethod = (args: any[], kwargs: any) => any;

interface ServerData {
  models: {
    [modelName: string]: ModelData,
  },
  actions: {
    [key: string]: Action,
  },
  views: {
    [key: string]: string,
  }
}
interface ModelMethods {[methodName: string]: ModelMethod}


/**
 * EXTENSION POINT: methods defined will be called with the data of the model as "this"
 */
export const standardModelMethodsRegistry: ModelMethods = {
  load_views: loadViews,
};
/*
 * BASIC MODEL METHODS
 */
function loadViews(this: ModelData) {
  console.log('loadViews', this);
}

export function makeFakeModelService(
  modelData?: ServerData['models'],
  mockCallModel?: ModelMethods
): any {
  const localData: ServerData['models'] = modelData || {};
  function callModel(model: string) {
    return (method: string, args = [], kwargs = {}) => {
      let res;
      const localModel = localData && localData[model] || {};
      if (mockCallModel && method in mockCallModel) {
        res = mockCallModel[method].call(localModel, args, kwargs);
      }
      if (res === undefined && method in standardModelMethodsRegistry) {
        res = standardModelMethodsRegistry[method].call(localModel, args, kwargs);
      }
      return Promise.resolve(res);
    };
  }
  const modelService: Service<Partial<ModelBuilder>> = {
    name: "model",
    deploy(env: OdooEnv) {
      return function (this: Component | null, model: string): Partial<Model> {
        return {
          get call() {
            return callModel(model);
          }
        };
      };
    },
  };
  return modelService;
}

/*function makeMockServer() {

}*/
/*
 * BASIC OTHER CONTROLLER METHODS
 */
/*function loadAction(data: ServerData['models'], actionId: ActionRequest, ...args: any[]) {
  return data.actions[actionId];
}*/
