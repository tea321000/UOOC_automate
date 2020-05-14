import sys
import requests
import json
import time
import os
import calendar
from http.cookies import SimpleCookie
import os
import subprocess


class baseGetJson():
    """创建基类"""

    def __init__(self, cookie: str):
        # print(cookie)
        # self.cookie=SimpleCookie()
        # self.cookie.load(cookie)
        # # del self.cookie['formhash']
        # ts = calendar.timegm(time.gmtime())
        # for key in self.cookie:
        #     if 'Hm_lpvt' in key:
        #         # 更新时间戳
        #         key=ts
        # # 再转换回str
        # print(self.cookie)
        # self.cookie_str = "; ".join([str(x)[12:] for x in self.cookie.items()])
        # print(self.cookie_str)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
            'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
            'Accept': 'application/json, text/plain, */*',
            'Content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Connection': 'keep-alive',
            'Referer': 'http://www.uooc.net.cn/home/learn/index',
            'Cookie': cookie
        }

    def send_request(self, url: str):
        """http get方法"""
        session = requests.Session()
        session.headers = self.headers
        res = session.get(url)
        assert res.status_code == 200, "网页返回状态码异常"
        return json.loads(res.text)


class GetCourses(baseGetJson):
    """获取课程列表及选择课程"""

    def __init__(self, cookie: str, url: str):
        baseGetJson.__init__(self, cookie)
        self.url = url

    def get_course_id(self):
        res = self.send_request(self.url)
        # print(res)
        for index, courseList in enumerate(res['data']['data']):
            print('第', index, '门课程：', courseList['parent_name'])
        print('输入对应课程索引获取课程id：')
        course_num = int(input())
        courseId = res['data']['data'][course_num]['id']
        print('课程id为：', courseId)
        return courseId


class GetCatalog(baseGetJson):
    """获取课程目录"""

    def __init__(self, cookie: str, url: str, course_id):
        baseGetJson.__init__(self, cookie)
        self.url = url % course_id
        self.courseId = course_id

    def get_available_catalog_dict(self):
        res = self.send_request(self.url)
        catalog = {}
        for chapter in res['data']:
            # 该章可用且尚未完成且不为测验
            if chapter['status'] != "0" and chapter['finished'] == 0 and chapter['task_id'] == 0:
                catalog[self.courseId] = {}
                children = chapter['children']
                for section in children:
                    # 该节可用且尚未完成且不为测验
                    if section['status'] != "0" and section['finished'] == 0 and section['task_id'] == 0:
                        catalog[self.courseId][chapter['id']] = {}
                        # 查询是否有二级目录
                        subsections = section.get('children', [])
                        if len(subsections) != 0:
                            catalog[self.courseId][chapter['id']][section['id']] = {}
                            for subsection in subsections:
                                # 该子节可用且尚未完成且不为测验
                                if subsection['status'] != "0" and subsection['finished'] == 0 and subsection['task_id'] == 0:
                                    catalog[self.courseId][chapter['id']][section['id']][subsection['id']] = []
                        else:
                            catalog[self.courseId][chapter['id']][section['id']] = []

        return catalog


class GetUnit(baseGetJson):
    """获取视频资源id"""

    def __init__(self, cookie, url, catalog):
        baseGetJson.__init__(self, cookie)
        self.catalog = catalog
        self.url = url

    def get_video_id(self):
        for course in self.catalog:
            for chapter in self.catalog[course]:
                for section in self.catalog[course][chapter]:
                    # 有二级目录
                    if type(self.catalog[course][chapter][section]) is dict:
                        for subsection in self.catalog[course][chapter][section]:
                            req_url = self.url % (subsection, chapter, course, section, subsection)
                            res = self.send_request(req_url)
                            for video in res['data']:
                                # 视频未完成
                                if video['finished'] == 0:
                                    self.catalog[course][chapter][section][subsection].append(
                                        {'id': video['id'], 'title': video['title'], 'video_url': video['video_url'],
                                         'pos': float(video['video_pos'])})
                    else:
                        # 没有二级目录就去掉后面的subsection
                        req_url = self.url.split('&subsection_id')[0] % (section, chapter, course, section)
                        res = self.send_request(req_url)
                        for video in res['data']:
                            # 视频未完成
                            if video['finished'] == 0:
                                self.catalog[course][chapter][section].append(
                                    {'id': video['id'], 'title': video['title'], 'video_url': video['video_url'],
                                     'pos': float(video['video_pos'])})
        return self.catalog


class MarkVideo(baseGetJson):
    """上传学习进度"""

    def __init__(self, cookie, url, catalog, ffmpeg_path):
        baseGetJson.__init__(self, cookie)
        self.catalog = catalog
        self.url = url
        self.ffmpeg_path = ffmpeg_path

    def send_request(self, url: str, form: dict):
        """http post方法"""
        print(form)
        res = requests.request("POST", url, headers=self.headers, data=form)
        assert res.status_code == 200, "网页返回状态码异常"
        return json.loads(res.text)

    def mark_video(self):
        """遍历所有更新视频学习标记"""
        for course in self.catalog:
            for chapter in self.catalog[course]:
                for section in self.catalog[course][chapter]:
                    # 有二级目录
                    if type(self.catalog[course][chapter][section]) is dict:
                        for subsection in self.catalog[course][chapter][section]:
                            for video in self.catalog[course][chapter][section][subsection]:
                                self.watch_video(course, chapter, section, video, subsection)
                    else:
                        for video in self.catalog[course][chapter][section]:
                            self.watch_video(course, chapter, section, video)

    def get_video_length(self, filename):
        """获取视频长度"""
        result = subprocess.run([self.ffmpeg_path, "-v", "error", "-show_entries",
                                 "format=duration", "-of",
                                 "default=noprint_wrappers=1:nokey=1", filename],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        # 保留两位小数，四舍五入
        return round(float(result.stdout), 2)

    def download_video(self, link):
        """下载视频并用ffmpeg返回视频长度"""
        file_name = 'tmp' + os.path.splitext(link)[1]
        with open(file_name, "wb") as f:
            print('正在下载视频以确定视频长度：', link[link.rfind('/') + 1:])
            session = requests.Session()
            session.headers = self.headers
            res = session.get(link, stream=True)
            total_length = res.headers.get('content-length')
            if total_length is None:
                f.write(res.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in res.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    done = int(50 * dl / total_length)
                    sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50 - done)))
                    sys.stdout.flush()
        length = self.get_video_length(file_name)
        # os.remove(file_name)
        return length

    def watch_video(self, course, chapter, section, video, subsection=None):
        """循环更新单个视频观看进度"""
        form = {}
        form['chapter_id'] = chapter
        form['cid'] = course
        form['hidemsg_'] = 'true'
        # 默认选择第一条网络线路
        form['network'] = 1
        form['resource_id'] = video['id']
        form['section_id'] = section
        # 默认选择第一个播放源
        form['source'] = 1
        for index, source in enumerate(video['video_url']):
            print('第', index + 1, '个源：', video['video_url'][source]['source_name'], '地址：',
                  video['video_url'][source]['source'])
            if form['source'] == index + 1:
                download_link = video['video_url'][source]['source']
        print('当前使用第', form['source'], '个源')
        if subsection is not None:
            form['subsection_id'] = subsection
        form['video_length'] = self.download_video(download_link)
        print('视频长度：', form['video_length'])
        form['video_pos'] = "%.2f" % video['pos']
        print('当前播放：', video['title'], '位置：', video['pos'])
        res = self.send_request(self.url, form)
        print('返回json:', res)
        while res['data']['finished'] == 0:
            print('尚未观看完成，60秒后再次上传观看进度，请等待')
            for i in range(0, 60):
                sys.stdout.write("\r[%s%s]" % ('=' * i, ' ' * (60 - i)))
                time.sleep(1)
            video['pos'] += 120
            if video['pos'] >= form['video_length'] - 1:
                video['pos'] = form['video_length']
            form['video_pos'] = "%.2f" % video['pos']
            print('\n当前播放：', video['title'], '位置：', video['pos'])
            res = self.send_request(self.url, form)
        print(video['title'], '观看完成')


if __name__ == '__main__':
    # 需要配置ffmpeg路径以及cookie
    ffmpeg_path = os.path.join('./ffmpeg-20200513-b12b053-win64-static', 'bin', "ffprobe.exe")
    cookie = ''
    # 定义好的网页接口
    url = {
        'courseId': 'http://www.uooc.net.cn/home/course/list?page=1&type=learn',
        'catalogList': 'http://www.uooc.net.cn/home/learn/getCatalogList?cid=%s&hidemsg=true&show=',
        'unitLearn': 'http://www.uooc.net.cn/home/learn/getUnitLearn?catalog_id=%s&chapter_id=%s&cid=%s&hidemsg=true&section_id=%s&show=&subsection_id=%s',
        'markVideoLearn': 'http://www.uooc.net.cn/home/learn/markVideoLearn/'
    }
    # 列出课程列表 用户输入获得课程id
    Courses = GetCourses(cookie, url['courseId'])
    courseId = Courses.get_course_id()
    # 获取课程目录结构（除视频id）
    Catalog = GetCatalog(cookie, url['catalogList'], courseId)
    catalogList = Catalog.get_available_catalog_dict()
    print(catalogList)
    # 将目录更新为带有视频id的
    Unit = GetUnit(cookie, url['unitLearn'], catalogList)
    catalogList = Unit.get_video_id()
    # 更新未完成视频的学习标记
    Video = MarkVideo(cookie, url['markVideoLearn'], catalogList, ffmpeg_path)
    Video.mark_video()
