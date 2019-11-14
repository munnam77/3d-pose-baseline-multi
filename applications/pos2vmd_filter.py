#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from PyQt5.QtGui import QQuaternion, QVector4D, QVector3D, QMatrix4x4
import logging
import json
import math

logger = logging.getLogger("__main__").getChild(__name__)

# フィルターをかける
def smooth_filter(bone_frame_dic, is_groove, smooth_times):

    # まず球形補間
    smooth_move(bone_frame_dic, is_groove, smooth_times)
    smooth_angle(bone_frame_dic, smooth_times)
    smooth_IK(bone_frame_dic, smooth_times)
    
    # JSONファイルから設定を読み込む
    config = json.load(open("filter/config.json", "r"))

    # 移動用フィルタ
    pxfilter = OneEuroFilter(**config)
    pyfilter = OneEuroFilter(**config)
    pzfilter = OneEuroFilter(**config)

    # 回転用フィルタ
    rxfilter = OneEuroFilter(**config)
    ryfilter = OneEuroFilter(**config)
    rzfilter = OneEuroFilter(**config)
    rwfilter = OneEuroFilter(**config)

    for key in bone_frame_dic.keys():
        for n, frame in enumerate(bone_frame_dic[key]):
            if key == "グルーブ" and is_groove == False:
                continue

            if "ＩＫ" in key:

                # IKの場合、次のフレームと全く同値の場合、フィルタをかけない
                if frame.frame < len(bone_frame_dic[key]) - 1 \
                and frame.position == bone_frame_dic[key][n+1].position \
                and frame.rotation == bone_frame_dic[key][n+1].rotation:
                    
                    # 位置と回転が同じ場合、同値とみなす
                    logger.debug("IK同値: %s %s", n, frame.name)

                    # 処理をスキップして次に行く
                    pxfilter.skip(frame.position.x(), frame.frame)
                    pyfilter.skip(frame.position.y(), frame.frame)
                    pzfilter.skip(frame.position.z(), frame.frame)

                    rxfilter.skip(frame.rotation.x(), frame.frame)
                    ryfilter.skip(frame.rotation.y(), frame.frame)
                    rzfilter.skip(frame.rotation.z(), frame.frame)
                    rwfilter.skip(frame.rotation.scalar(), frame.frame)

                    continue

            # XYZそれぞれにフィルターをかける
            px = pxfilter(frame.position.x(), frame.frame)
            py = pyfilter(frame.position.y(), frame.frame)
            pz = pzfilter(frame.position.z(), frame.frame)
            frame.position = QVector3D(px, py, pz)

            rotation = frame.rotation

            # 同じ回転を表すクォータニオンが正負2通りあるので、wの符号が正のほうに統一する
            # if rotation.scalar() < 0:
            #     rotation.setX(rotation.x() * -1)
            #     rotation.setY(rotation.y() * -1)
            #     rotation.setZ(rotation.z() * -1)
            #     rotation.setScalar(rotation.scalar() * -1)
            
            if key != "センター" and key != "グルーブ":
                # XYZWそれぞれにフィルターをかける
                rx = rxfilter(rotation.x(), frame.frame)
                ry = ryfilter(rotation.y(), frame.frame)
                rz = rzfilter(rotation.z(), frame.frame)
                rw = rwfilter(rotation.scalar(), frame.frame)

                # 各要素(w, x, y, z)に対し独立に変換をかけているので、正規化しておく
                frame.rotation = QQuaternion(rw, rx, ry, rz).normalized()
    


# IKを滑らかにする
def smooth_IK(bone_frame_dic, smooth_times):
    target_bones = ["左足ＩＫ", "右足ＩＫ"]

    # 関節の角度円滑化
    smooth_angle_bone(bone_frame_dic, smooth_times, target_bones)

    # 移動の位置円滑化
    smooth_move_bone(bone_frame_dic, smooth_times, target_bones)

# 回転を滑らかにする
def smooth_angle(bone_frame_dic, smooth_times):
    # 角度をなめらかに
    smooth_angle_bone(bone_frame_dic, smooth_times, ["上半身", "上半身2", "下半身", "首", "頭", "左肩", "左腕", "左ひじ", "右肩",  "右腕", "右ひじ", "左足", "左ひざ", "右足", "右ひざ"])

# 回転を滑らかにする
def smooth_angle_bone(bone_frame_dic, smooth_times, target_bones):
    # 関節の角度円滑化
    for bone_name in target_bones:
        for n in range(smooth_times):
            for frame in range(len(bone_frame_dic[bone_name])):
                if frame >= 2:
                    prev2_bf = bone_frame_dic[bone_name][frame - 2]
                    prev1_bf = bone_frame_dic[bone_name][frame - 1]
                    now_bf = bone_frame_dic[bone_name][frame]

                    if prev2_bf != now_bf.rotation:
                        # 角度が違っていたら、球形補正開始
                        prev1_bf.rotation = QQuaternion.slerp(prev2_bf.rotation, now_bf.rotation, 0.5)

def smooth_move(bone_frame_dic, is_groove, smooth_times):
    # センターを滑らかに
    if is_groove:
        smooth_move_bone(bone_frame_dic, smooth_times, ["センター", "グルーブ"])
    else:
        smooth_move_bone(bone_frame_dic, smooth_times, ["センター"])


def smooth_move_bone(bone_frame_dic, smooth_times, target_bones):
    # 移動の位置円滑化
    for bone_name in target_bones:
        for n in range(smooth_times):
            for frame in range(len(bone_frame_dic[bone_name])):
                if frame >= 4:
                    prev2_bf = bone_frame_dic[bone_name][frame - 2]
                    prev1_bf = bone_frame_dic[bone_name][frame - 1]
                    now_bf = bone_frame_dic[bone_name][frame]

                    # 移動ボーンのどこかが動いていたら
                    if now_bf != prev2_bf:
                        # 線形補正
                        new_prev1_pos = prev2_bf.position + now_bf.position
                        new_prev1_pos /= 2
                        prev1_bf.position = new_prev1_pos



# OneEuroFilter
# オリジナル：https://www.cristal.univ-lille.fr/~casiez/1euro/
# ----------------------------------------------------------------------------

class LowPassFilter(object):

    def __init__(self, alpha):
        self.__setAlpha(alpha)
        self.__y = self.__s = None

    def __setAlpha(self, alpha):
        alpha = float(alpha)
        if alpha<=0 or alpha>1.0:
            raise ValueError("alpha (%s) should be in (0.0, 1.0]"%alpha)
        self.__alpha = alpha

    def __call__(self, value, timestamp=None, alpha=None):        
        if alpha is not None:
            self.__setAlpha(alpha)
        if self.__y is None:
            s = value
        else:
            s = self.__alpha*value + (1.0-self.__alpha)*self.__s
        self.__y = value
        self.__s = s
        return s

    def lastValue(self):
        return self.__y
    
    # IK用処理スキップ
    def skip(self, value):
        self.__y = value
        self.__s = value

        return value

# ----------------------------------------------------------------------------

class OneEuroFilter(object):

    def __init__(self, freq, mincutoff=1.0, beta=0.0, dcutoff=1.0):
        if freq<=0:
            raise ValueError("freq should be >0")
        if mincutoff<=0:
            raise ValueError("mincutoff should be >0")
        if dcutoff<=0:
            raise ValueError("dcutoff should be >0")
        self.__freq = float(freq)
        self.__mincutoff = float(mincutoff)
        self.__beta = float(beta)
        self.__dcutoff = float(dcutoff)
        self.__x = LowPassFilter(self.__alpha(self.__mincutoff))
        self.__dx = LowPassFilter(self.__alpha(self.__dcutoff))
        self.__lasttime = None
        
    def __alpha(self, cutoff):
        te    = 1.0 / self.__freq
        tau   = 1.0 / (2*math.pi*cutoff)
        return  1.0 / (1.0 + tau/te)

    def __call__(self, x, timestamp=None):
        # ---- update the sampling frequency based on timestamps
        if self.__lasttime and timestamp:
            self.__freq = 1.0 / (timestamp-self.__lasttime)
        self.__lasttime = timestamp
        # ---- estimate the current variation per second
        prev_x = self.__x.lastValue()
        dx = 0.0 if prev_x is None else (x-prev_x)*self.__freq # FIXME: 0.0 or value?
        edx = self.__dx(dx, timestamp, alpha=self.__alpha(self.__dcutoff))
        # ---- use it to update the cutoff frequency
        cutoff = self.__mincutoff + self.__beta*math.fabs(edx)
        # ---- filter the given value
        return self.__x(x, timestamp, alpha=self.__alpha(cutoff))

    # IK用処理スキップ
    def skip(self, x, timestamp=None):
        # ---- update the sampling frequency based on timestamps
        if self.__lasttime and timestamp:
            self.__freq = 1.0 / (timestamp-self.__lasttime)
        self.__lasttime = timestamp
        prev_x = self.__x.lastValue()
        self.__dx.skip(prev_x)
        self.__x.skip(x)

