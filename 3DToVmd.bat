@echo off
rem --- 
rem ---  3D �� �֐߃f�[�^���� vmd�f�[�^�ɕϊ�
rem --- 

rem ---  �J�����g�f�B���N�g�������s��ɕύX
cd /d %~dp0

rem ---  INDEX�ʃf�B���N�g���p�X
echo INDEX�ʃf�B���N�g���̃t���p�X����͂��ĉ������B({���於}_json_{���s����}_idx00)
echo pos.txt�Ȃǂ̂���f�B���N�g���ł��B
echo ���̐ݒ�͔��p�p�����̂ݐݒ�\�ŁA�K�{���ڂł��B
echo ,(�J���})��5���܂Őݒ�\�ł��B
set TARGET_DIR=
set /P TARGET_DIR=��INDEX�ʃf�B���N�g���p�X: 
rem echo TARGET_DIR�F%TARGET_DIR%

IF /I "%TARGET_DIR%" EQU "" (
    ECHO INDEX�ʃf�B���N�g���p�X���ݒ肳��Ă��Ȃ����߁A�����𒆒f���܂��B
    EXIT /B
)


rem ---  �{�[���\��CSV�t�@�C��
echo --------------
set MODEL_BONE_CSV=born\���ɂ܂����~�N�{�[��.csv
echo �g���[�X�Ώۃ��f���̃{�[���\��CSV�t�@�C���̑��΂������͐�΃p�X����͂��ĉ������B
echo �������͂����AENTER�����������ꍇ�A�u%MODEL_BONE_CSV%�v�̃t�@�C����ǂݍ��݂܂��B
set /P MODEL_BONE_CSV="���{�[���\��CSV�t�@�C��: "

rem ---  FK or IK

echo --------------
echo ����IK�ŏo�͂��邩�Ayes �� no ����͂��ĉ������B
echo no ����͂����ꍇ�AFK�ŏo�͂��܂�
echo �������͂����AENTER�����������ꍇ�AIK�ŏo�͂��܂��B
set IK_FLAG=1
set IS_IK=yes
set /P IS_IK="����IK�o�͐���[yes/no]: "

IF /I "%IS_IK%" EQU "no" (
    set IK_FLAG=0
    set HEEL_POSITION=0
    rem -- FK�̏ꍇ�A���ʒu�␳�͍s��Ȃ�
    goto CONFIRM_CENTER
)

rem ---  ���ʒu�␳
echo --------------
set HEEL_POSITION=0
echo ����Y���␳�l�𐔒l(������)�œ��͂��ĉ������B
echo �}�C�i�X�l����͂���ƒn�ʂɋߕt���A�v���X�l����͂���ƒn�ʂ��牓������܂��B
echo ������x�͎����ŕ␳���܂����A�␳������Ȃ��ꍇ�ɁA�ݒ肵�ĉ������B
echo �������͂����AENTER�����������ꍇ�A�␳���s���܂���B
echo ,(�J���})��5���܂Őݒ�\�ł��B
set /P HEEL_POSITION="�����ʒu�␳: "


:CONFIRM_CENTER

rem ---  �Z���^�[XY�ړ��{��
rem echo --------------
set CENTER_XY_SCALE=30
rem echo �Z���^�[XY�ړ��Ɋ|����{���𐮐��œ��͂��ĉ������B
rem echo �l���������قǁA�Z���^�[XY�ړ��̕����������Ȃ�܂��B
rem echo �������͂����AENTER�����������ꍇ�A�{���u%CENTER_XY_SCALE%�v�ŏ������܂��B
rem echo ,(�J���})��5���܂Őݒ�\�ł��B
rem set /P CENTER_XY_SCALE="���Z���^�[XY�ړ��{��: "

rem ---  �Z���^�[Z�ړ��{��
echo --------------
set CENTER_Z_SCALE=0
echo �Z���^�[Z�ړ��Ɋ|����{���𐔒l(������)�œ��͂��ĉ������B
echo �l���������قǁA�Z���^�[Z�ړ��̕����������Ȃ�܂��B
echo �ڈ��Ƃ��āA�J��������̋������߂��قǁA�{�����������������������ł��B
echo �������͂����AENTER�����������ꍇ�A�{���u%CENTER_Z_SCALE%�v�ŏ������܂��B
echo 0����͂����ꍇ�A�Z���^�[Z���ړ����s���܂���B
echo ,(�J���})��5���܂Őݒ�\�ł��B
set /P CENTER_Z_SCALE="���Z���^�[Z�ړ��{��: "

rem ---  ���炩��

echo --------------
set SMOOTH_TIMES=1
echo ���[�V�����̉~�����̓x�����w�肵�܂�
echo 1�ȏ�̐����݂̂���͂��ĉ������B
echo �x�����傫���قǁA�~��������܂��B�i����ɓ��삪�������Ȃ�܂��j
echo �������͂����AENTER�����������ꍇ�A%SMOOTH_TIMES%��~�������܂��B
echo ,(�J���})��5���܂Őݒ�\�ł��B
set /P SMOOTH_TIMES="�~�����x��: "

rem ---  �ړ��Ԉ�����

echo --------------
set THRESHOLD_POS=0.5
echo �ړ��L�[�iIK�E�Z���^�[�j�̊Ԉ����Ɏg�p����ړ��ʂ𐔒l(������)�Ŏw�肵�܂�
echo �w�肳�ꂽ�͈͓��̈ړ����������ꍇ�ɊԈ�������܂��B
echo �������͂����AENTER�����������ꍇ�A�u%THRESHOLD_POS%�v�̈ړ��ʂŊԈ����܂��B
echo �ړ��Ԉ����ʂ�0�ɂ����ꍇ�A�Ԉ������s���܂���B
echo ,(�J���})��5���܂Őݒ�\�ł��B
set /P THRESHOLD_POS="���ړ��L�[�Ԉ�����: "

IF /I "%THRESHOLD_POS%" EQU "0" (
    rem -- �Ԉ������s��Ȃ�
    set THRESHOLD_POS=0
    set THRESHOLD_ROT=0

    goto CONFRIM_LOG
)
rem -- �Ԉ�������

rem ---  ��]�Ԉ����p�x

echo --------------
set THRESHOLD_ROT=3
echo ��]�L�[�̊Ԉ����Ɏg�p����p�x(0�`180�x�܂ŏ�����)���w�肵�܂�
echo �w�肳�ꂽ�p�x�ȓ��̉�]���������ꍇ�ɊԈ�������܂��B
echo �������͂����AENTER�����������ꍇ�A%THRESHOLD_ROT%�x�Ԉ����܂��B
echo ,(�J���})��5���܂Őݒ�\�ł��B
set /P THRESHOLD_ROT="����]�L�[�Ԉ����p�x: "


rem ---  �ڍ׃��O�L��

:CONFRIM_LOG

echo --------------
echo �ڍׂȃ��O���o�����Ayes �� no ����͂��ĉ������B
echo �������͂����AENTER�����������ꍇ�A�ʏ탍�O�̂ݏo�͂��܂��B
set VERBOSE=2
set IS_DEBUG=no
set /P IS_DEBUG="���ڍ׃��O[yes/no]: "

IF /I "%IS_DEBUG%" EQU "yes" (
    set VERBOSE=3
)

rem -----------------------------------------

rem -- �����t���[���o�͑Ώۃf�B���N�g���́A�����Ώۃf�B���N�g���Œ�
set UPRIGHT_TARGET_DIR=
for /F "tokens=1" %%a in ('echo %TARGET_DIR:,= %') do (
    set UPRIGHT_TARGET_DIR=%%a
)

rem -- baseline��͌��ʃf�B���N�g��
for %%u in (%TARGET_DIR%) do (
    rem -- ���ʒu�␳
    for %%h in (%HEEL_POSITION%) do (
        rem -- �Z���^�[XY�ړ��{��
        for %%x in (%CENTER_XY_SCALE%) do (
            rem -- �Z���^�[Z�ړ��{��
            for %%z in (%CENTER_Z_SCALE%) do (
                rem -- ���炩��
                for %%s in (%SMOOTH_TIMES%) do (
                    rem -- �ړ��Ԉ�����
                    for %%p in (%THRESHOLD_POS%) do (
                        rem -- ��]�Ԉ����p�x
                        for %%r in (%THRESHOLD_ROT%) do (
                            
                            echo -----------------------------
                            rem -- echo ���������f�B���N�g��: %UPRIGHT_TARGET_DIR%
                            echo baseline�f�B���N�g��: %%u
                            echo ���ʒu�␳: %%h
                            echo �Z���^�[XY�ړ��{��: %%x
                            echo �Z���^�[Z�ړ��{��: %%z
                            echo �~�����x��: %%s
                            echo �ړ��Ԉ�����: %%p
                            echo ��]�Ԉ����p�x: %%r
                            
                            rem ---  python ���s
                            python applications\pos2vmd_multi.py -v %VERBOSE% -t "%%u" -b %MODEL_BONE_CSV% -c %%x -z %%z -s %%s -p %%p -r %%r -k %IK_FLAG% -e %%h -u "%UPRIGHT_TARGET_DIR%"
                        )
                    )
                )
            )
        )
    )
)



