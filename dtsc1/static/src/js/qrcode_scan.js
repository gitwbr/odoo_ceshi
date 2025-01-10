/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller"; // 引入 FormController
import rpc from 'web.rpc'; // 引入 RPC 模块

// 使用 patch 直接扩展 FormController
console.log("Your dtsc FormController is loading...");
patch(FormController.prototype, 'dtsc.FormController', {
	setup() {
		this._super();
		console.log("setup 被调用");

		let attempts = 0; // 尝试次数
		const maxAttempts = 10; // 最大尝试次数

		const intervalId = setInterval(() => {
			const button = document.getElementById('scan_qr_button'); // 查找按钮
			const closebutton = document.getElementById('close_qr_button'); // 查找按钮

			if (button) {
				console.log("按钮已经找到: #scan_qr_button"); 
				button.addEventListener('click', () => this.startQRScanner()); // 绑定点击事件
				clearInterval(intervalId); // 找到按钮后清除定时器
				if(closebutton)
					closebutton.addEventListener('click', () => this.closeQRScanner());
			} else {
				attempts++;
				console.log("按钮未找到: #scan_qr_button");
				if (attempts >= maxAttempts) {
					console.log("达到最大尝试次数，退出。");
					clearInterval(intervalId); // 达到最大尝试次数后清除定时器
				}
			}
		}, 1000); // 每秒检查一次
	},
	// console.log("222222222222222222222");
	closeQRScanner:function(){
		const qrReaderElement = document.getElementById("qr-reader"); // 获取用于显示摄像头的元素
        
        if (!qrReaderElement) {
            console.error("找不到 ID 为 qr-reader 的元素");
            return;
        }
		if (this.html5QrCode) {
            this.html5QrCode.stop().then(() => {
                console.log("摄像头已关闭");
                qrReaderElement.style.display = "none"; // 隐藏 QR 码读取器
                this.html5QrCode = null; // 清除实例
            }).catch(err => {
                console.error("停止扫描时出错:", err);
            });
        } else {
            // 如果没有实例，直接隐藏
            qrReaderElement.style.display = "none"; 
        }
	},

    startQRScanner: function () {
        // 创建 Html5Qrcode 实例并启动扫描
		const qrReaderElement = document.getElementById("qr-reader"); // 获取用于显示摄像头的元素
        
        if (!qrReaderElement) {
            console.error("找不到 ID 为 qr-reader 的元素");
            return;
        }

        // 显示 QR 码读取器
        qrReaderElement.style.display = "block"; 
        const html5QrCode = new Html5Qrcode("qr-reader");
		
		
		qrReaderElement.style.display = "block"; 
        // 启动二维码扫描
        html5QrCode.start(
            { facingMode: "environment" },
            {
                fps: 10,
                qrbox: 250
            },
            (decodedText) => {
                console.log("扫描到的二维码:", decodedText);
                this.callPythonMethod(decodedText); // 调用 Python 方法
                html5QrCode.stop(); // 停止扫描
				qrReaderElement.style.display = "none"; 
            },
            (errorMessage) => {
                console.warn(`QR code scan error: ${errorMessage}`);
            }
        ).catch(err => {
            console.error("Unable to start scanning: ", err);
        });
    },

    callPythonMethod: function (qrCodeData) {
        // 调用后端 Python 方法
        rpc.query({
            model: 'dtsc.installproduct',  // 替换为你的模型
            method: 'process_qr_code',  // 替换为你的方法名
            args: [[],[qrCodeData]],  // 传递扫描到的二维码数据
        }).then(result => {
            console.log("Python 方法返回的结果:", result);
            // 可选：根据需要处理返回结果
        }).catch(error => {
            console.error("调用 Python 方法出错:", error);
        });
    },
});