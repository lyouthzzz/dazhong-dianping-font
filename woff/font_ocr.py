from collections import OrderedDict
import io
import hashlib
import setting

class DianPingFont():
    def __init__(self, cache_maxlen=100):
        self.cache_maxlen = cache_maxlen
        self.id_words_cache = OrderedDict()  # unicode -> word 字典
        self.fontDraw = FontDraw()
        self.fontOcr = FontOcr()

    def ocr_one(self, unicode, font_io):
        """
        :param unicode: 待识别的unicode字体
        :param font_io: woff字体库二进制流
        :return:
        """
        font_id = self._get_bytes_md5(font_io.read())

        unicode_word_dict = self.id_words_cache.get(font_id) if font_id in self.id_words_cache else {}

        if unicode_word_dict.get(unicode):
            return unicode_word_dict.get(unicode)

        # 画图
        font_image = self.fontDraw.draw_one(unicode, font_io)
        # ocr
        word = self.fontOcr.ocr(font_image)

        if len(self.id_words_cache) >= self.cache_maxlen:
            # 删除font-unicode-word-dict 前75%
            for _i in range(int(self.cache_maxlen * 0.75)):
                self.id_words_cache.popitem(last=False)

        # 保存识别记录
        unicode_word_dict[unicode] = word
        self.id_words_cache[font_id] = unicode_word_dict

        return word

    def ocr_all(self, font_io):
        # md5 作为唯一id
        font_id = self._get_bytes_md5(font_io.read())
        if font_id in self.id_words_cache:
            return self.id_words_cache.get(font_id)

        unicode_word_dict = {}
        # 画图
        unicode_image_dict = self.fontDraw.draw_all(font_io)
        for unicode, image in unicode_image_dict.items():
            # ocr
            word = self.fontOcr.ocr(image)
            print(unicode + ' : ' + str(word))
            unicode_word_dict[unicode] = word

        if len(self.id_words_cache) >= self.cache_maxlen:
            # 删除font-unicode-word-dict 前75%
            for _i in range(int(self.cache_maxlen * 0.75)):
                self.id_words_cache.popitem(last=False)

        # 保存识别记录
        self.id_words_cache[font_id] = unicode_word_dict
        return unicode_word_dict


    def _get_bytes_md5(self, bytes):
        hl = hashlib.md5()
        hl.update(bytes)
        return hl.hexdigest()

from aip import AipOcr

baidu_api_ocr = AipOcr(setting.APP_ID, setting.API_KEY, setting.SECRET_KEY)

class FontOcr():
    def __init__(self, language_type='CHN_ENG', detect_language=False):
        self.ocr_option = {
            'language_type': language_type,
            'detect_language': detect_language
        }

    def ocr(self, image):
        try:
            if not isinstance(image, (Image.Image, bytes)):
                return None
            if (isinstance(image, Image.Image)):
                io_bytes = io.BytesIO()
                image.save(io_bytes, format='JPEG')
                image = io_bytes.getvalue()

            """ 通用文字识别 """
            general_resp = baidu_api_ocr.basicGeneral(image)

            if general_resp['words_result_num'] == 1:
                word = general_resp['words_result'][0]['words']
                if len(word) == 1:
                    return word

            """ 通用文字识别（高精度版） """
            accurate_resp = baidu_api_ocr.basicAccurate(image)
            if accurate_resp['words_result_num'] == 1:
                word = accurate_resp['words_result'][0]['words']
                if len(word) == 1:
                    return word
        except Exception as e:
            # todo error日志
            pass
        return None


from PIL import Image
from reportlab.graphics.shapes import Group, Drawing
from reportlab.graphics import renderPM
from reportlab.lib import colors
from fontTools.ttLib import TTFont
from reportlab.graphics.shapes import Path
from fontTools.pens import reportLabPen


class FontDraw():
    def __init__(self):
        # 画出的字体缩放
        self.font_scale = 0.1

    def draw_one(self, unicode, font_io):
        ttf_font = TTFont(font_io)
        glyphSet = ttf_font.getGlyphSet()
        if unicode not in glyphSet:
            return None
        glyph = glyphSet[unicode]
        pen = reportLabPen.ReportLabPen(glyphSet, Path(fillColor=colors.black, strokeWidth=1))
        glyph.draw(pen)

        w, h = glyph.width, glyph._glyph.yMax - glyph._glyph.yMin
        yOffset = -glyph._glyph.yMin * \
                  self.font_scale + h * (1 - self.font_scale) / 2
        glyph = Group(pen.path)
        glyph.translate(w * (1 - self.font_scale) / 2, yOffset)
        glyph.scale(self.font_scale, self.font_scale)
        draw = Drawing(w, h)
        draw.add(glyph)
        PIL_image = renderPM.drawToPIL(draw)
        return PIL_image

    def draw_all(self, font_io):
        ttf_font = TTFont(font_io)
        glyphSet = ttf_font.getGlyphSet()
        font_image_dict = {}
        for glyphName in glyphSet.keys():
            if (not glyphName.startswith('uni')):
                continue
            pen = reportLabPen.ReportLabPen(glyphSet, Path(fillColor=colors.black, strokeWidth=1))
            glyph = glyphSet[glyphName]
            glyph.draw(pen)

            w, h = glyph.width, glyph._glyph.yMax - glyph._glyph.yMin
            yOffset = -glyph._glyph.yMin * \
                      self.font_scale + h * (1 - self.font_scale) / 2
            glyph = Group(pen.path)
            glyph.translate(w * (1 - self.font_scale) / 2, yOffset)
            glyph.scale(self.font_scale, self.font_scale)
            draw = Drawing(w, h)
            draw.add(glyph)
            PIL_image = renderPM.drawToPIL(draw)
            font_image_dict[glyphName] = PIL_image
        return font_image_dict



if __name__ == "__main__":
    # font_path = '5b0ad8bda40cc82dfb2e009a80893543.woff'
    # with open(font_path, mode='rb') as f:
    #     font_bytes = f.read()
    # font_io = io.BytesIO(font_bytes)
    # dianping_font = DianPingFont()
    # import time
    # start = time.time()
    # for unicode in ['unie10e', 'unief2c', 'unie768', 'unie127', 'uni65f', 'unif86e', 'unif4ce', 'unie149', 'unie0f3', 'unif826']:
    #     _word = dianping_font.ocr_one(unicode, font_io)
    #     print(_word)
    # print(time.time()-start)
    # # print(_word)
    # # unicode_word_dict = dianping_font.ocr_all(font_io)
    # font_io.close()
    pass
