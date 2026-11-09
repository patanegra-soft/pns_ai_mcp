/** @odoo-module **/
/**
 * Show LLM usage chip after server detection suggest (form + list).
 *
 * SPDX-License-Identifier: Apache-2.0
 * Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
 */

import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { setUsageElementsWithFx } from "./ai_usage_chip";

const MODEL = "ai.api.server";

async function showServerUsage(controller, usage) {
    const el = controller.rootRef();
    if (!usage || !el) {
        return;
    }
    const orm = controller.env.services.orm;
    const root = el.closest(".o_content") || el;
    await setUsageElementsWithFx(orm, root, usage);
}

async function runSuggestDetection(controller, resIds) {
    const orm = controller.env.services.orm;
    const call = (orm.silent && typeof orm.silent.call === "function")
        ? orm.silent.call.bind(orm.silent)
        : orm.call.bind(orm);
    const action = await call(MODEL, "action_suggest_detection", [resIds]);
    if (action && action.usage) {
        await showServerUsage(controller, action.usage);
    }
    if (action && action.type) {
        await controller.env.services.action.doAction(action);
    }
}

patch(FormController.prototype, {
    async beforeExecuteActionButton(clickParams) {
        if (
            this.props.resModel === MODEL
            && clickParams
            && clickParams.name === "action_suggest_detection"
        ) {
            await runSuggestDetection(this, [this.model.root.resId]);
            return false;
        }
        return super.beforeExecuteActionButton(clickParams);
    },
});

patch(ListController.prototype, {
    async beforeExecuteActionButton(clickParams) {
        if (
            this.props.resModel === MODEL
            && clickParams
            && clickParams.name === "action_suggest_detection"
        ) {
            let resIds = [];
            if (typeof this.model.root.getResIds === "function") {
                resIds = await this.model.root.getResIds(true);
            } else if (this.model.root.records) {
                resIds = this.model.root.records.map((rec) => rec.resId);
            }
            await runSuggestDetection(this, resIds);
            return false;
        }
        return super.beforeExecuteActionButton(clickParams);
    },
});
