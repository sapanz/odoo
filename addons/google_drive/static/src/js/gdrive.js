odoo.define("google_drive/static/src/js/gdrive", function (require) {
    "use strict";

    const ActionMenus = require("web.ActionMenus");

    async function googleDriveItemGetter(env, props, rpc) {
        if (env.view.type !== "form" || !props.activeIds[0]) {
            return [];
        }

        const items = await rpc({
            args: [env.action.res_model, props.activeIds[0]],
            context: props.context,
            method: "get_google_drive_config",
            model: "google.drive.config",
        });

        return items.map(item => Object.assign(item, {
            async callback() {
                const resID = props.activeIds[0];
                const domain = [["id", "=", item.id]];
                const fields = ["google_drive_resource_id", "google_drive_client_id"];
                const configs = await rpc({
                    args: [domain, fields],
                    method: "search_read",
                    model: "google.drive.config",
                });
                const url = await rpc({
                    args: [item.id, resID, configs[0].google_drive_resource_id],
                    context: props.context,
                    method: "get_google_drive_url",
                    model: "google.drive.config",
                });
                if (url) {
                    window.open(url, "_blank");
                }
            },
            description: item.name,
        }));
    }

    ActionMenus.registry.add("google-drive", googleDriveItemGetter);

    return googleDriveItemGetter;
});
