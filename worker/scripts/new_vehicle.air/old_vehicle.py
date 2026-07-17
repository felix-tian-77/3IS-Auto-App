# -*- encoding=utf8 -*-
__author__ = "felixtian"

from airtest.core.api import *

auto_setup(__file__)



from poco.drivers.android.uiautomation import AndroidUiautomationPoco
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)

import os

# ---- Parameters (injected by Worker via environment variables) ----
transaction_id = os.environ.get("TRANSACTION_ID")
holder_phone   = os.environ.get("HOLDER_PHONE")
customer_phone = os.environ.get("CUSTOMER_PHONE")
business_type  = os.environ.get("BUSINESS_TYPE")
tax_exempt     = os.environ.get("TAX_EXEMPT", "false").lower() == "true"
is_transfer    = os.environ.get("IS_TRANSFER", "false").lower() == "true"

# 手机号 fallback：优先客户手机号，其次被保险人手机号，最后测试默认值
mobile_phone = customer_phone or holder_phone or "19110898582"

poco("畅销宝").click()
poco("车险").wait_for_appearance(timeout=10)
poco("车险").click()
poco(text="立即投保").wait_for_appearance(timeout=10)
poco(text="立即投保").click()

poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[0].child("android.view.View").child("android.view.View").child("android.view.View")[1].click()

poco(text="修文1部/26001506").click()
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[2].child("android.view.View").child("android.view.View").child("android.view.View")[1].click()
wait(Template(r"tpl1783819120439.png", record_pos=(0.031, 1.049), resolution=(1080, 2520)), timeout=None, interval=0.5)

touch(Template(r"tpl1783819145870.png", record_pos=(-0.001, 1.056), resolution=(1080, 2520)))

poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[4].child("android.view.View").child("android.view.View").child("android.view.View")[1].child("android.view.View").child("android.view.View").child("android.view.View").child("android.view.View")[1].click()
poco(text="名称：刘松龄").click()
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[6].child("android.view.View").child("android.view.View").child("android.view.View")[1].offspring("android.widget.Image").click()
wait(Template(r"tpl1783819873896.png", record_pos=(0.021, 0.919), resolution=(1080, 2520)), timeout=None, interval=0.5)
touch(Template(r"tpl1783819873896.png", record_pos=(0.021, 0.919), resolution=(1080, 2520)))
poco(text="行驶证").click()
poco("com.android.intentresolver:id/bottom_sheet_view").offspring("com.android.intentresolver:id/chooser_nested_scroll_view").offspring("android:id/profile_tabhost").offspring("android:id/profile_pager").offspring("android:id/resolver_list").child("android.widget.LinearLayout")[1].offspring("com.android.intentresolver:id/icon").click()
poco("更多选项").click()
poco("com.android.providers.media.module:id/title").click()
poco("android.widget.FrameLayout").child("android.widget.LinearLayout").offspring("com.google.android.documentsui:id/drawer_layout").offspring("com.google.android.documentsui:id/apps_row").offspring("com.google.android.documentsui:id/apps_group").child("android.widget.LinearLayout")[2].child("com.google.android.documentsui:id/app_icon").click()
poco(text="内部存储设备").click()
poco(text="3is").click()
poco(text=transaction_id).click()
poco(text="DRIVING_LICENSE_FRONT.jpg").click()
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").swipe([0.0591, -0.5299])
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[10].child("android.view.View")[2].child("android.view.View").click()
poco(text="投保单录入").click()

if exists(Template(r"tpl1783822204848.png", record_pos=(-0.007, -0.231), resolution=(1080, 2520))):
  poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[6].child("android.view.View").child("android.view.View")[0].child("android.view.View").child("android.view.View").click()
  poco(text="确定").click()

poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[10].swipe([0.069, -0.7685])

# 输入最高设计车速
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[3].child("android.view.View").child("android.view.View").child("android.view.View")[1].child("android.view.View").child("android.view.View").child("android.view.View").child("android.view.View")[1].child("android.widget.TextView").click()


poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[3].child("android.view.View").child("android.view.View").child("android.view.View")[1].child("android.view.View").child("android.view.View").child("android.view.View").child("android.view.View")[1].offspring("android.widget.EditText").set_text("80")

#touch(Template(r"tpl1783825709290.png", record_pos=(-0.131, 0.887), resolution=(1080, 2520)))
#touch(Template(r"tpl1783825716102.png", record_pos=(-0.144, 1.034), resolution=(1080, 2520)))

#touch(Template(r"tpl1783825723964.png", record_pos=(0.367, 0.954), resolution=(1080, 2520)))


poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[4].child("android.view.View").child("android.view.View")[1].offspring("android.widget.Image").click()

wait(Template(r"tpl1783822819833.png", record_pos=(-0.019, 1.054), resolution=(1080, 2520)), timeout=None, interval=0.5)

touch(Template(r"tpl1783822819833.png", record_pos=(-0.019, 1.054), resolution=(1080, 2520)))


#选择身份证正反面
poco(text="身份证(正反面)").click()

poco("com.android.intentresolver:id/bottom_sheet_view").offspring("com.android.intentresolver:id/chooser_nested_scroll_view").offspring("android:id/profile_tabhost").offspring("android:id/profile_pager").offspring("android:id/resolver_list").child("android.widget.LinearLayout")[1].offspring("com.android.intentresolver:id/icon").click()
poco("更多选项").click()
poco("com.android.providers.media.module:id/title").click()
poco("android.widget.FrameLayout").child("android.widget.LinearLayout").offspring("com.google.android.documentsui:id/drawer_layout").offspring("com.google.android.documentsui:id/apps_row").offspring("com.google.android.documentsui:id/apps_group").child("android.widget.LinearLayout")[2].child("com.google.android.documentsui:id/app_icon").click()
poco(text="内部存储设备").click()
poco(text="3is").click()
poco(text=transaction_id).click()
poco(text="ID_CARD_FRONT.jpg").click()
poco(text="身份证(正反面)").click()
poco("com.android.intentresolver:id/bottom_sheet_view").offspring("com.android.intentresolver:id/chooser_nested_scroll_view").offspring("android:id/profile_tabhost").offspring("android:id/profile_pager").offspring("android:id/resolver_list").child("android.widget.LinearLayout")[1].offspring("com.android.intentresolver:id/icon").click()
poco("更多选项").click()
poco("com.android.providers.media.module:id/title").click()
poco("android.widget.FrameLayout").child("android.widget.LinearLayout").offspring("com.google.android.documentsui:id/drawer_layout").offspring("com.google.android.documentsui:id/apps_row").offspring("com.google.android.documentsui:id/apps_group").child("android.widget.LinearLayout")[2].child("com.google.android.documentsui:id/app_icon").click()
poco(text="内部存储设备").click()
poco(text="3is").click()
poco(text=transaction_id).click()
poco(text="ID_CARD_BACK.jpg").click()


#完成身份证选择

#输入手机号

poco("android.widget.FrameLayout").offspring("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[9].child("android.view.View").child("android.view.View").child("android.view.View")[1].child("android.view.View").child("android.view.View").child("android.view.View").offspring("android.widget.EditText").set_text(mobile_phone)




    

















