# -*- encoding=utf8 -*-
__author__ = "felix"

from airtest.core.api import *

auto_setup(__file__)


from poco.drivers.android.uiautomation import AndroidUiautomationPoco
poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)


poco("车险").click()
poco(text="立即投保").swipe([0.0033, 0.0])

#选择承保机构
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[0].child("android.view.View").child("android.view.View").child("android.view.View")[1].click()
poco(text="修文1部/26001506").click()

#选择业务来源
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[2].child("android.view.View").child("android.view.View").child("android.view.View")[1].click()
touch(Template(r"tpl1784256486669.png", record_pos=(0.021, 1.055), resolution=(1080, 2520)))




poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[4].child("android.view.View").child("android.view.View").child("android.view.View")[1].child("android.view.View").child("android.view.View").child("android.view.View").child("android.view.View")[1].click()
poco(text="编码：A202626191288").click()


poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[6].child("android.view.View").child("android.view.View").child("android.view.View")[1].offspring("android.widget.Image").click()
touch(Template(r"tpl1784256688481.png", record_pos=(0.011, 0.92), resolution=(1080, 2520)))


poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[13].child("android.view.View")[0].click()

#上传新车合格证
poco(text="新车合格证").click()
poco(text="媒体选择工具").click()
poco("更多选项").click()
poco("com.android.providers.media.module:id/title").click()
poco(text="文件管理").click()
poco(text="内部存储设备").click()
poco(text="3is").click()
poco(text="01.png").click()
     
     
poco(text="投保单录入").click()

     
#上传新车合格证
poco(text="新车合格证").click()
poco(text="媒体选择工具").click()
poco("更多选项").click()
poco("com.android.providers.media.module:id/title").click()
poco(text="文件管理").click()
poco(text="内部存储设备").click()
poco(text="3is").click()
poco(text="01.jpg").click()

#行驶证车辆
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[5].child("android.view.View").child("android.view.View").child("android.view.View")[1].click()
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[5].child("android.view.View").child("android.view.View").child("android.view.View")[1].child("android.view.View")[1].child("android.view.View").child("android.view.View").child("android.view.View").child("android.view.View").child("android.view.View")[1].child("android.view.View").child("android.widget.TextView").child("android.widget.TextView").click()

#向下滚动
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[9].swipe([0.0997, -0.4813])

#过户情况
poco("android:id/content").child("android.webkit.WebView").offspring("app").child("android.view.View").child("android.view.View")[9].child("android.view.View").child("android.view.View")[1].child("android.view.View").click()
touch(Template(r"tpl1784257693294.png", record_pos=(-0.009, 0.931), resolution=(1080, 2520)))


#上传身份证
poco(text="身份证(正反面)").click()
poco(text="媒体选择工具").click()
poco("更多选项").click()
poco("com.android.providers.media.module:id/title").click()
poco(text="文件管理").click()
poco(text="内部存储设备").click()
poco(text="3is").click()
poco(text="03.jpg").click()


