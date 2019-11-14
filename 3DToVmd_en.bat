@echo off
rem --- 
rem ---  Convert 3D joint data to vmd data
rem --- 

rem ---  Change the current directory to the execution destination
cd /d %~dp0

rem ---  Individual directory path
echo Please enter the full path of individual index directory.({Movie name}_json_{Execution date and time}_idx00)
echo There is a directory such as pos.txt.
echo This setting is available only in Half - width alphanumeric characters and is mandatory.
set TARGET_DIR=
set /P TARGET_DIR=** Individual directory path: 
rem echo TARGET_DIR：%TARGET_DIR%

IF /I "%TARGET_DIR%" EQU "" (
    ECHO Since the individual directory path of the index is not set, processing is interrupted.
    EXIT /B
)


rem ---  Bone structure CSV file
echo --------------
set MODEL_BONE_CSV=born\animasa_miku_born.csv
echo Enter the relative or absolute path of the bone structure CSV file of the trace target model.
echo If nothing is entered and ENTER is pressed, the file of "%MODEL_BONE_CSV%" is read.
set /P MODEL_BONE_CSV="** Bone structure CSV file: "

rem ---  FK or IK

echo --------------
echo Please output your feet with IK, or enter yes or no.
echo If you enter no, output it with FK
echo If nothing is entered and ENTER is pressed, it is output with IK.
set IK_FLAG=1
set IS_IK=yes
set /P IS_IK="** Foot IK Whether to output[yes/no]: "

IF /I "%IS_IK%" EQU "no" (
    set IK_FLAG=0
    set HEEL_POSITION=0
    rem -- FKの場合、踵位置補正は行わない
    goto CONFIRM_CENTER
)

rem ---  踵位置補正
echo --------------
set HEEL_POSITION=0
echo Please input the Y axis correction value of the heel with a numerical value (decimal possible).
echo Entering a negative value approaches the ground, entering a positive value moves away from the ground.
echo Although it corrects automatically to some extent automatically, if you can not correct it, please set it.
echo If you do not enter anything and press ENTER, no correction will be made.
echo You can set up to 5 items by separating them with a comma.
set /P HEEL_POSITION="** Heel position correction: "


:CONFIRM_CENTER

rem ---  センターXY移動倍率
rem echo --------------
set CENTER_XY_SCALE=30
rem echo Please enter the multiplication factor for center XY movement as an integer.
rem echo The smaller the value, the smaller the width of the center XY movement.
rem echo If nothing is entered and ENTER is pressed, processing is performed with the magnification "%CENTER_XY_SCALE%".
rem echo You can set up to 5 items by separating them with a comma.
rem set /P CENTER_XY_SCALE="** Center XY Magnification: "

rem ---  センターZ移動倍率
echo --------------
set CENTER_Z_SCALE=0
echo Please enter the magnification multiplied by the center Z movement with a numerical value (decimal possible).
echo The smaller the value, the smaller the width of the center Z movement.
echo As a guide, it is better to reduce the magnification as the distance from the camera is shorter.
echo If nothing is entered and ENTER is pressed, processing is performed with the magnification "%CENTER_Z_SCALE%".
echo When 0 is input, center Z axis movement is not performed.
echo You can set up to 5 items by separating them with a comma.
set /P CENTER_Z_SCALE="** Center Z moving magnification: "

rem ---  滑らかさ

echo --------------
set SMOOTH_TIMES=1
echo Specify the degree of motion smoothing
echo Please enter only an integer of 1 or more.
echo The larger the frequency, the smoother it is. (The behavior will be smaller instead)
echo If nothing is entered and ENTER is pressed, it smoothes %SMOOTH_TIMES% times.
echo You can set up to 5 items by separating them with a comma.
set /P SMOOTH_TIMES="** Smoothing frequency: "

rem ---  移動間引き量

echo --------------
set THRESHOLD_POS=0.5
echo Specify the amount of movement to be used for decimation of movement key (IK, center) with numerical value (decimal possible)
echo When there is a movement within the specified range, it is thinned out.
echo If nothing is entered and ENTER is pressed, thinning is performed with the movement amount of "%THRESHOLD_POS%".
echo When moving thinning amount is set to 0, thinning is not performed.
echo You can set up to 5 items by separating them with a comma.
set /P THRESHOLD_POS="** Movement key thinning amount: "

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
echo Specify the angle (decimal possible from 0 to 180 degrees) to be used for decimating rotation keys
echo It will be thinned out if there is a rotation within the specified angle.
echo If you do not enter anything and you press ENTER, %THRESHOLD_ROT% censor.
echo You can set up to 5 items by separating them with a comma.
set /P THRESHOLD_ROT="** Rotating Key Culling Angle: "


rem ---  詳細ログ有無

:CONFRIM_LOG

echo --------------
echo Please output detailed logs or enter yes or no.
echo If nothing is entered and ENTER is pressed, only the normal log is output.
set VERBOSE=2
set IS_DEBUG=no
set /P IS_DEBUG="■Detailed log[yes/no]: "

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
                            echo baseline directory: %%u
                            echo Heel position correction: %%h
                            echo Center XY movement magnification: %%x
                            echo Center Z moving magnification: %%z
                            echo Smoothness: %%s
                            echo Movement thinning amount: %%p
                            echo Rotation thinning angle: %%r
                            
                            rem ---  python 実行
                            python applications\pos2vmd_multi.py -v %VERBOSE% -t "%%u" -b %MODEL_BONE_CSV% -c %%x -z %%z -s %%s -p %%p -r %%r -k %IK_FLAG% -e %%h -u "%UPRIGHT_TARGET_DIR%"
                        )
                    )
                )
            )
        )
    )
)



