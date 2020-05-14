# UOOC_automate
UOOC优课联盟自动化播放

由于http接口中无法获得视频长度`video_length`，因此从视频源下载课程视频并使用ffmpeg获得视频的长度。
设置cookie方法：
1. （以chrome浏览器为例）访问[课程列表页面](http://www.uooc.net.cn/home/course/list?page=1&type=learn)按下F12或右键检查打开开发者工具，切换到network选项卡；
2. 刷新页面，network栏下点击name栏中任意一个元素,右侧Header栏中request headers->cookies里的内容复制到程序的cookie中
3. 运行程序后会列出该账号下所有课程，输入课程相应的数字对该课程进行自动化播放

假如跑完一次还有漏掉的视频再运行一次

![运行截图](https://github.com/tea321000/UOOC_automate/blob/master/img/%E8%BF%90%E8%A1%8C%E6%88%AA%E5%9B%BE.jpg?raw=true "运行截图")
