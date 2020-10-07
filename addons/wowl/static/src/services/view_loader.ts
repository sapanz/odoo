import { Service, ServiceParams } from "../services";
import { ViewType } from "../views/types";

interface ViewLoader {
  loadView(model: string, type: ViewType, viewId?: number | false): Promise<ViewDefinition>;
}

interface ViewDefinition {
  arch: string;
  type: ViewType;
  viewId: number;
}

export const viewLoaderService: Service<ViewLoader> = {
  name: "view_loader",
  dependencies: ["model"],
  deploy(params: ServiceParams): ViewLoader {
    const { env } = params;
    const modelService = env.services.model;

    const loadView = async (model: string, type: ViewType, viewId: number | false = false) => {
      const data = await modelService(model).call("load_views", [], {
        options: { toolbar: true },
        views: [[viewId, type]],
      });
      const viewData = data.fields_views[type];
      return { arch: viewData.arch, viewId: viewData.view_id, type };
    };
    return { loadView };
  },
};
