# -*- encoding=utf8 -*-
__author__ = "felixtian"

from airtest.core.api import *

auto_setup(__file__)



from poco.drivers.android.uiautomation import AndroidUiautomationPoco
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)
#poco("畅销宝").click()
poco("车险").wait_for_appearance(timeout=10)
poco("车险").click()
poco(text="立即投保").wait_for_appearance(timeout=10)
poco(text="立即投保").click()
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[0].child("android.view.View").child("android.view.View").child("android.view.View")[1].click()
poco(text="修文1部/26001506").click()
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[2].child("android.view.View").child("android.view.View").child("android.view.View")[1].click()
wait(Template(r"tpl1783819120439.png", record_pos=(0.031, 1.049), resolution=(1080, 2520)), timeout=None, interval=0.5)

touch(Template(r"tpl1783819145870.png", record_pos=(-0.001, 1.056), resolution=(1080, 2520)))








