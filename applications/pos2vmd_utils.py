#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from PyQt5.QtGui import QQuaternion, QVector4D, QVector3D, QMatrix4x4
import logging
import csv
import re
import os
import numpy as np

from VmdWriter import VmdWriter, VmdInfoIk, VmdShowIkFrame
from VmdReader import VmdReader, VmdMotion

logger = logging.getLogger("__main__").getChild(__name__)

def output_vmd(bone_frame_dic, vmd_file, upright_idxs, is_ik, vmd_type):
    writer = VmdWriter()
    
    # ディクショナリ型の疑似二次元配列から、一次元配列に変換
    bone_frames = []
    for k,v in bone_frame_dic.items():
        for bf in v:
            bone_frames.append(bf)

    # vmd出力ファイルにフレーム番号再設定
    output_vmd_file = vmd_file.replace("[uDDDD]", "u{0:05d}".format(upright_idxs[0]))
    output_vmd_file = output_vmd_file.replace("[type]", vmd_type)

    # writer.write_vmd_file(vmd_file, bone_frames, showik_frames, expression_frames)
    showik_frames = make_showik_frames(is_ik)
    writer.write_vmd_file(output_vmd_file, bone_frames, showik_frames)

    return output_vmd_file

# 調整直立情報取得
def load_upright_target(upright_target):

    target_upright_depth = 0
    target_upright_idx = 0
    target_start_pos = {}

    # 初期値
    target_start_pos["center"] = QVector3D()
    for key in ["Neck", "RHip", "LHip", "RKnee", "LKnee", "RAnkle", "LAnkle"]:
        target_start_pos[key] = QVector3D()

    if upright_target is not None:
        path = upright_target +"/upright.txt"
        logger.debug("path: %s %s", path, os.path.exists(path))
        if os.path.exists(path):
            # 直立調整対象ファイルが存在する場合
            with open(path, "r") as bf:
                # 直立IDX
                target_upright_idx = int(bf.readline())

                # 0Fセンターpos
                while True:
                    s_line = bf.readline()

                    if not s_line:
                        break

                    # 直立の各数値取得
                    poss = s_line.split(",")
                    target_start_pos[poss[0]] = QVector3D()
                    target_start_pos[poss[0]].setX(float(poss[1]))
                    target_start_pos[poss[0]].setY(float(poss[2]))
                    target_start_pos[poss[0]].setZ(float(poss[3]))
            
    # logger.info("target_start_pos")
    # logger.info(target_start_pos)

    return target_upright_idx, target_upright_depth, target_start_pos



# センターY軸をグルーブY軸に移管
def set_groove(bone_frame_dic, bone_csv_file):

    # グルーブボーンがあるか
    is_groove = False
    # ボーンファイルを開く
    with open(bone_csv_file, "r", encoding=get_file_encoding(bone_csv_file)) as bf:
        reader = csv.reader(bf)

        for row in reader:
            if row[1] == "グルーブ" or row[2].lower() == "groove":
                is_groove = True
                break

    if is_groove:

        for n in range(len(bone_frame_dic["センター"])):
            # logger.debug("グルーブ移管 frame={0}".format(n))

            # グルーブがある場合、Y軸をグルーブに設定
            bone_frame_dic["グルーブ"][n].position = QVector3D(0, bone_frame_dic["センター"][n].position.y(), 0)
            bone_frame_dic["センター"][n].position = QVector3D(bone_frame_dic["センター"][n].position.x(), 0, bone_frame_dic["センター"][n].position.z())

    return is_groove



# 初期傾きモーションデータ読み込み
def load_slope_vmd(is_upper2_body):
    reader = VmdReader()
    if is_upper2_body:
        # 上半身2がある場合
        return reader.read_vmd_file("slope/slope_upper2.vmd")
    else:
        # 標準ボーンのみの場合
        return reader.read_vmd_file("slope/slope_normal.vmd")



# 開始フレームを取得
def load_start_frame(start_frame_file):
    n = 0
    with open(start_frame_file, "r") as sf:
        return int(sf.readline())



#複数フレームの読み込み
def read_positions_multi(position_file):
    """Read joint position data"""
    f = open(position_file, "r")

    positions = []
    while True:
        line = f.readline()
        if not line:
            break
        line = line.rstrip('\n')

        # 一旦カンマで複数行に分解
        inposition = []
        for inline in re.split(",\s*", line):
            if inline:
                # 1フレーム分に分解したら、空白で分解
                a = re.split(' ', inline)
                # print(a)
                # 元データはz軸が垂直上向き。MMDに合わせるためにyとzを入れ替える。
                q = QVector3D(float(a[1]), float(a[3]), float(a[2])) # a[0]: index
                inposition.append(q) # a[0]: index
        
        positions.append(inposition)
    f.close()
    return positions


DEPTH_INDEX = {
    "index": 0,
    "Nose": 1,
    "Neck": 2,
    "RShoulder": 3,
    "RElbow": 4,
    "RWrist": 5,
    "LShoulder": 6,
    "LElbow": 7,
    "LWrist": 8,
    "RHip": 9,
    "RKnee": 10,
    "RAnkle": 11,
    "LHip": 12,
    "LKnee": 13,
    "LAnkle": 14,
    "REye": 15,
    "LEye": 16,
    "REar": 17,
    "LEar": 18
}

# depthファイルの読み込み
def load_depth(depth_file):
    if os.path.exists(depth_file) == False:
        return None

    depths = [[0 for i in range(len(DEPTH_INDEX))] for j in range(sum(1 for line in open(depth_file)))]

    n = 0
    # 深度ファイルからフレームINDEXを取得する
    with open(depth_file, "r") as bf:
        # カンマ区切りなので、csvとして読み込む
        reader = csv.reader(bf)

        for row in reader:
            # logger.debug("row[0] {0}, row[1]: {1}, row[2]: {2}, row[3]: {3}".format(row[0], row[1], row[2], row[3]))
            depths[n][DEPTH_INDEX["index"]] = int(row[0])
            depths[n][DEPTH_INDEX["Nose"]] = float(row[1])
            depths[n][DEPTH_INDEX["Neck"]] = float(row[2])
            depths[n][DEPTH_INDEX["RShoulder"]] = float(row[3])
            depths[n][DEPTH_INDEX["RElbow"]] = float(row[4])
            depths[n][DEPTH_INDEX["RWrist"]] = float(row[5])
            depths[n][DEPTH_INDEX["LShoulder"]] = float(row[6])
            depths[n][DEPTH_INDEX["LElbow"]] = float(row[7])
            depths[n][DEPTH_INDEX["LWrist"]] = float(row[8])
            depths[n][DEPTH_INDEX["RHip"]] = float(row[9])
            depths[n][DEPTH_INDEX["RKnee"]] = float(row[10])
            depths[n][DEPTH_INDEX["RAnkle"]] = float(row[11])
            depths[n][DEPTH_INDEX["LHip"]] = float(row[12])
            depths[n][DEPTH_INDEX["LKnee"]] = float(row[13])
            depths[n][DEPTH_INDEX["LAnkle"]] = float(row[14])
            depths[n][DEPTH_INDEX["REye"]] = float(row[15])
            depths[n][DEPTH_INDEX["LEye"]] = float(row[16])
            depths[n][DEPTH_INDEX["REar"]] = float(row[17])
            depths[n][DEPTH_INDEX["LEar"]] = float(row[18])
        
            n += 1

    return depths

SMOOTHED_2D_INDEX = {
    "Nose": 0,
    "Neck": 1,
    "RShoulder": 2,
    "RElbow": 3,
    "RWrist": 4,
    "LShoulder": 5,
    "LElbow": 6,
    "LWrist": 7,
    "RHip": 8,
    "RKnee": 9,
    "RAnkle": 10,
    "LHip": 11,
    "LKnee": 12,
    "LAnkle": 13,
    "REye": 14,
    "LEye": 15,
    "REar": 16,
    "LEar": 17,
    "Background": 18
}

# 関節2次元情報を取得
def load_smoothed_2d(smoothed_file):
    # １次元：フレーム数分
    # ２次元：OpenposeのINDEX分
    smoothed_2d = [[0 for i in range(19)] for j in range(sum(1 for line in open(smoothed_file)))]
    n = 0
    with open(smoothed_file, "r") as sf:
        line = sf.readline() # 1行を文字列として読み込む(改行文字も含まれる)
        
        while line:
            # 空白で複数項目に分解
            smoothed = re.split("\s+", line)

            # logger.debug(smoothed)

            # 首の位置
            smoothed_2d[n][SMOOTHED_2D_INDEX["Neck"]] = QVector3D(float(smoothed[2]), float(smoothed[3]), 0)
            # 右足付け根
            smoothed_2d[n][SMOOTHED_2D_INDEX["RHip"]] = QVector3D(float(smoothed[16]), float(smoothed[17]), 0)
            # 左足付け根
            smoothed_2d[n][SMOOTHED_2D_INDEX["LHip"]] = QVector3D(float(smoothed[22]), float(smoothed[23]), 0)
            # 右ひざ
            smoothed_2d[n][SMOOTHED_2D_INDEX["RKnee"]] = QVector3D(float(smoothed[18]), float(smoothed[19]), 0)
            # 左ひざ
            smoothed_2d[n][SMOOTHED_2D_INDEX["LKnee"]] = QVector3D(float(smoothed[24]), float(smoothed[25]), 0)
            # 右足首
            smoothed_2d[n][SMOOTHED_2D_INDEX["RAnkle"]] = QVector3D(float(smoothed[20]), float(smoothed[21]), 0)
            # 左足首
            smoothed_2d[n][SMOOTHED_2D_INDEX["LAnkle"]] = QVector3D(float(smoothed[26]), float(smoothed[27]), 0)
        
            n += 1

            line = sf.readline()
    
    return smoothed_2d

# ファイルのエンコードを取得する
def get_file_encoding(file_path):

    try: 
        f = open(file_path, "rb")
        fbytes = f.read()
        f.close()
    except:
        raise Exception("unknown encoding!")
        
    codelst = ('utf_8', 'shift-jis')
    
    for encoding in codelst:
        try:
            fstr = fbytes.decode(encoding) # bytes文字列から指定文字コードの文字列に変換
            fstr = fstr.encode('utf-8') # uft-8文字列に変換
            # 問題なく変換できたらエンコードを返す
            logger.debug("%s: encoding: %s", file_path, encoding)
            return encoding
        except:
            pass
            
    raise Exception("unknown encoding!")
    
    
# 上半身2があるか    
def is_upper2_body_bone(bone_csv_file):

    # ボーンファイルを開く
    with open(bone_csv_file, "r", encoding=get_file_encoding(bone_csv_file)) as bf:
        reader = csv.reader(bf)

        for row in reader:
            if row[1] == "上半身2" or row[2].lower() == "upper body2":
                return True
    
    return False


# 直立姿勢から傾いたところの頂点を求める
# FIXME クォータニオンで求められないか要調査
def calc_slope_point(upright, rx, ry, rz):
    # // ｘ軸回転
    # x1 = dat[n][0] ;
    # y1 = dat[n][1]*cos(rx)-dat[n][2]*sin(rx) ;
    # z1 = dat[n][1]*sin(rx)+dat[n][2]*cos(rx) ;
    x1 = upright.x()
    y1 = upright.y() * np.cos(np.radians(rx)) - upright.z() * np.sin(np.radians(rx))
    z1 = upright.y() * np.sin(np.radians(rx)) + upright.z() * np.cos(np.radians(rx))

    # // ｙ軸回転
    # x2 = x1*cos(ry)+z1*sin(ry) ;
    # y2 = y1 ;
    # z2 = z1*cos(ry)-x1*sin(ry) ;
    x2 = x1 * np.cos(np.radians(ry)) + z1 * np.sin(np.radians(ry))
    y2 = y1
    z2 = z1 * np.cos(np.radians(ry)) - x1 * np.sin(np.radians(ry))

    # // ｚ軸回転
    # x3 = x2*cos(rz)-y2*sin(rz) ;
    # y3 = x2*sin(rz)+y2*cos(rz) ;
    # z3 = z2 ;
    x3 = x2 * np.cos(np.radians(rz)) - y2 * np.sin(np.radians(rz))
    y3 = x2 * np.sin(np.radians(rz)) + y2 * np.cos(np.radians(rz))
    z3 = z2

    return QVector3D(x3, y3, z3)

# 3つの頂点から三角形の面積を計算する
def calc_triangle_area(a, b, c):
    # logger.debug(a)
    # logger.debug(b)
    # logger.debug(c)
    # logger.debug("(a.y() - c.y())")
    # logger.debug((a.y() - c.y()))
    # logger.debug("(b.x() - c.x())")
    # logger.debug((b.x() - c.x()))
    # logger.debug("(b.y() - c.y())")
    # logger.debug((b.y() - c.y()))
    # logger.debug("(c.x() - a.x())")
    # logger.debug((c.x() - a.x()))
    return abs(( ((a.y() - c.y()) * (b.x() - c.x())) \
                    + ((b.y() - c.y()) * (c.x() - a.x())) ) / 2 )
    


def make_showik_frames(is_ik):
    onoff = 1 if is_ik == True else 0

    frames = []
    sf = VmdShowIkFrame()
    sf.show = 1
    sf.ik.append(VmdInfoIk(b'\x8d\xb6\x91\xab\x82\x68\x82\x6a', onoff)) # '左足ＩＫ'
    sf.ik.append(VmdInfoIk(b'\x89\x45\x91\xab\x82\x68\x82\x6a', onoff)) # '右足ＩＫ'
    sf.ik.append(VmdInfoIk(b'\x8d\xb6\x82\xc2\x82\xdc\x90\xe6\x82\x68\x82\x6a', onoff)) # '左つまＩＫ'
    sf.ik.append(VmdInfoIk(b'\x89\x45\x82\xc2\x82\xdc\x90\xe6\x82\x68\x82\x6a', onoff)) # '右つまＩＫ'
    frames.append(sf)
    return frames
