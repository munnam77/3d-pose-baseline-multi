@echo off
rem --- 
rem ---  3D の 関節データから vmdデータに変換
rem --- 

rem ---  カレントディレクトリを実行先に変更
cd /d %~dp0

rem ---  INDEX別ディレクトリパス
echo INDEX別ディレクトリのフルパスを入力して下さい。({動画名}_json_{実行日時}_idx00)
echo pos.txtなどのあるディレクトリです。
echo この設定は半角英数字のみ設定可能で、必須項目です。
echo ,(カンマ)で5件まで設定可能です。
set TARGET_DIR=
set /P TARGET_DIR=■INDEX別ディレクトリパス: 
rem echo TARGET_DIR：%TARGET_DIR%

IF /I "%TARGET_DIR%" EQU "" (
    ECHO INDEX別ディレクトリパスが設定されていないため、処理を中断します。
    EXIT /B
)


rem ---  ボーン構造CSVファイル
echo --------------
set MODEL_BONE_CSV=born\あにまさ式ミクボーン.csv
echo トレース対象モデルのボーン構造CSVファイルの相対もしくは絶対パスを入力して下さい。
echo 何も入力せず、ENTERを押下した場合、「%MODEL_BONE_CSV%」のファイルを読み込みます。
set /P MODEL_BONE_CSV="■ボーン構造CSVファイル: "

rem ---  FK or IK

echo --------------
echo 足をIKで出力するか、yes か no を入力して下さい。
echo no を入力した場合、FKで出力します
echo 何も入力せず、ENTERを押下した場合、IKで出力します。
set IK_FLAG=1
set IS_IK=yes
set /P IS_IK="■足IK出力是非[yes/no]: "

IF /I "%IS_IK%" EQU "no" (
    set IK_FLAG=0
    set HEEL_POSITION=0
    rem -- FKの場合、踵位置補正は行わない
    goto CONFIRM_CENTER
)

rem ---  踵位置補正
echo --------------
set HEEL_POSITION=0
echo 踵のY軸補正値を数値(小数可)で入力して下さい。
echo マイナス値を入力すると地面に近付き、プラス値を入力すると地面から遠ざかります。
echo ある程度は自動で補正しますが、補正しきれない場合に、設定して下さい。
echo 何も入力せず、ENTERを押下した場合、補正を行いません。
echo ,(カンマ)で5件まで設定可能です。
set /P HEEL_POSITION="■踵位置補正: "


:CONFIRM_CENTER

rem ---  センターXY移動倍率
rem echo --------------
set CENTER_XY_SCALE=30
rem echo センターXY移動に掛ける倍率を整数で入力して下さい。
rem echo 値が小さいほど、センターXY移動の幅が小さくなります。
rem echo 何も入力せず、ENTERを押下した場合、倍率「%CENTER_XY_SCALE%」で処理します。
rem echo ,(カンマ)で5件まで設定可能です。
rem set /P CENTER_XY_SCALE="■センターXY移動倍率: "

rem ---  センターZ移動倍率
echo --------------
set CENTER_Z_SCALE=0
echo センターZ移動に掛ける倍率を数値(小数可)で入力して下さい。
echo 値が小さいほど、センターZ移動の幅が小さくなります。
echo 目安として、カメラからの距離が近いほど、倍率を小さくした方がいいです。
echo 何も入力せず、ENTERを押下した場合、倍率「%CENTER_Z_SCALE%」で処理します。
echo 0を入力した場合、センターZ軸移動を行いません。
echo ,(カンマ)で5件まで設定可能です。
set /P CENTER_Z_SCALE="■センターZ移動倍率: "

rem ---  滑らかさ

echo --------------
set SMOOTH_TIMES=1
echo モーションの円滑化の度数を指定します
echo 1以上の整数のみを入力して下さい。
echo 度数が大きいほど、円滑化されます。（代わりに動作が小さくなります）
echo 何も入力せず、ENTERを押下した場合、%SMOOTH_TIMES%回円滑化します。
echo ,(カンマ)で5件まで設定可能です。
set /P SMOOTH_TIMES="円滑化度数: "

rem ---  移動間引き量

echo --------------
set THRESHOLD_POS=0.5
echo 移動キー（IK・センター）の間引きに使用する移動量を数値(小数可)で指定します
echo 指定された範囲内の移動があった場合に間引きされます。
echo 何も入力せず、ENTERを押下した場合、「%THRESHOLD_POS%」の移動量で間引きます。
echo 移動間引き量を0にした場合、間引きを行いません。
echo ,(カンマ)で5件まで設定可能です。
set /P THRESHOLD_POS="■移動キー間引き量: "

IF /I "%THRESHOLD_POS%" EQU "0" (
    rem -- 間引きを行わない
    set THRESHOLD_POS=0
    set THRESHOLD_ROT=0

    goto CONFRIM_LOG
)
rem -- 間引きする

rem ---  回転間引き角度

echo --------------
set THRESHOLD_ROT=3
echo 回転キーの間引きに使用する角度(0～180度まで小数可)を指定します
echo 指定された角度以内の回転があった場合に間引きされます。
echo 何も入力せず、ENTERを押下した場合、%THRESHOLD_ROT%度間引きます。
echo ,(カンマ)で5件まで設定可能です。
set /P THRESHOLD_ROT="■回転キー間引き角度: "


rem ---  詳細ログ有無

:CONFRIM_LOG

echo --------------
echo 詳細なログを出すか、yes か no を入力して下さい。
echo 何も入力せず、ENTERを押下した場合、通常ログのみ出力します。
set VERBOSE=2
set IS_DEBUG=no
set /P IS_DEBUG="■詳細ログ[yes/no]: "

IF /I "%IS_DEBUG%" EQU "yes" (
    set VERBOSE=3
)

rem -----------------------------------------

rem -- 直立フレーム出力対象ディレクトリは、処理対象ディレクトリ固定
set UPRIGHT_TARGET_DIR=
for /F "tokens=1" %%a in ('echo %TARGET_DIR:,= %') do (
    set UPRIGHT_TARGET_DIR=%%a
)

rem -- baseline解析結果ディレクトリ
for %%u in (%TARGET_DIR%) do (
    rem -- 踵位置補正
    for %%h in (%HEEL_POSITION%) do (
        rem -- センターXY移動倍率
        for %%x in (%CENTER_XY_SCALE%) do (
            rem -- センターZ移動倍率
            for %%z in (%CENTER_Z_SCALE%) do (
                rem -- 滑らかさ
                for %%s in (%SMOOTH_TIMES%) do (
                    rem -- 移動間引き量
                    for %%p in (%THRESHOLD_POS%) do (
                        rem -- 回転間引き角度
                        for %%r in (%THRESHOLD_ROT%) do (
                            
                            echo -----------------------------
                            rem -- echo 直立調整ディレクトリ: %UPRIGHT_TARGET_DIR%
                            echo baselineディレクトリ: %%u
                            echo 踵位置補正: %%h
                            echo センターXY移動倍率: %%x
                            echo センターZ移動倍率: %%z
                            echo 円滑化度数: %%s
                            echo 移動間引き量: %%p
                            echo 回転間引き角度: %%r
                            
                            rem ---  python 実行
                            python applications\pos2vmd_multi.py -v %VERBOSE% -t "%%u" -b %MODEL_BONE_CSV% -c %%x -z %%z -s %%s -p %%p -r %%r -k %IK_FLAG% -e %%h -u "%UPRIGHT_TARGET_DIR%"
                        )
                    )
                )
            )
        )
    )
)



