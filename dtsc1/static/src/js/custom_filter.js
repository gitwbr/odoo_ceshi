/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FilterMenu } from "@web/search/filter_menu/filter_menu";
import { CustomFilterItem } from "@web/search/filter_menu/custom_filter_item";
import { useService } from "@web/core/utils/hooks"; // 确保使用 useService 引入

export class CustomFilterItemOverride extends CustomFilterItem {
    setup() {
        super.setup();
        this.rpc = require('web.rpc');

        const viewId = this.env.searchModel?.config?.viewId || this.env.config?.viewId;
        if (!viewId) {
            console.error("viewId is undefined");
            return;
        }
        console.log("View ID (Numeric):", viewId);

        // 通过 RPC 获取外部 ID
        this.rpc.query({
			model: 'ir.model.data',
			method: 'search_read',
			args: [
				[['model', '=', 'ir.ui.view'], ['res_id', '=', viewId]],
				['module', 'name']
			],
		}).then((result) => {
			if (result.length > 0) {
				const externalId = `${result[0].module}.${result[0].name}`;
				console.log("External ID:", externalId);

				if (externalId === 'dtsc.view_makeoutt_tree' || externalId === 'dtsc.view_makein_tree') {
					console.log('Applying filter for delivery_date field');
					this.fields = this.fields.filter(field => field.name === 'delivery_date');
					console.log("Filtered fields: ", this.fields);
					// 确保条件和初始状态的正确设置
					this.conditions = [{
						field: this.fields.findIndex(field => field.name === 'delivery_date'),
						operator: 0,  // 默认操作符
						value: [new Date()],
					}];
					// 强制刷新组件以应用新的 fields
					this.render();
				}
			} else {
				console.log("External ID not found for this view.");
			}
		}).catch((error) => {
			console.error("Error accessing viewId or searchModel:", error);
		});
    }
}

export class FilterMenuOverride extends FilterMenu {
    setup() {
        super.setup();
        console.log("FilterMenuOverride loaded");
    }
}

FilterMenuOverride.components.CustomFilterItem = CustomFilterItemOverride;
registry.category("components").add("FilterMenu", FilterMenuOverride);
