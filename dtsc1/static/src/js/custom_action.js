/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { ActionMenus } from "@web/search/action_menus/action_menus";

// 使用 patch 直接扩展 ActionMenus
patch(ActionMenus.prototype, 'dtsc.ActionMenus', {
    async setActionItems(props) {
        // 调用父类的原始方法
        const items = await this._super(props);

        // 获取 formattedActions 并打印原始内容
        const actionActions = props.items.action || [];
        let formattedActions = actionActions.map((action) => ({
            action,
            description: action.name,
            key: action.id,
        }));
        console.log('Original formattedActions:', formattedActions);

        // 初始化 RPC 调用
        const rpc = require('web.rpc');
        
        // 获取当前页面的 viewId
        const viewId = this.env.searchModel?.config?.viewId || this.env.config?.viewId;
        if (!viewId) {
            console.error("viewId is undefined");
            return [...items];  // 返回原始 items，避免错误
        }
        console.log("View ID (Numeric):", viewId);

        // 使用 RPC 获取视图的外部 ID
        return rpc.query({
            model: 'ir.model.data',
            method: 'search_read',
            args: [
                [['model', '=', 'ir.ui.view'], ['res_id', '=', viewId]],
                ['module', 'name']
            ],
        }).then((result) => {
            let externalId = '';
            if (result.length > 0) {
                externalId = `${result[0].module}.${result[0].name}`;
                console.log("External ID:", externalId);

                // 根据视图 ID 过滤动作
                if (externalId === 'dtsc.view_checkout_tree') {
                    formattedActions = formattedActions.filter(action => 
                        action.description !== '轉出貨單' && 
                        action.description !== '轉應收單' && 
                        action.description !== '追加單據'
                    );
                    console.log('Filtered formattedActions based on view:', formattedActions);
                }
            }

            // 返回过滤后的 items，结合原有的 callbackActions 和 registryActions 等
           /*  const callbackActions = (props.items.other || []).map((action) =>
                Object.assign({ key: `action-${action.description}` }, action)
            ); */
			let callbackActions = (props.items.other || []).map((action) =>
                Object.assign({ key: `action-${action.description}` }, action)
            );
			
			callbackActions = callbackActions.filter(action => action.key !== 'export');
			
            const registryActions = []; // 如果有其他 registryActions 处理，可以在此补充
            return [...callbackActions, ...formattedActions, ...registryActions];
        }).catch((error) => {
            console.error("Error fetching external ID via RPC:", error);
            // 在出现错误时，依然返回初始 items
            return [...items];
        });
    }
});
