#!/usr/bin/python

# This script is used to generate luabinding glue codes.
# Android ndk version must be ndk-r9b.


import sys
import os, os.path
import shutil
import ConfigParser
import subprocess
import re
from contextlib import contextmanager


def _check_ndk_root_env():
    ''' Checking the environment NDK_ROOT, which will be used for building
    '''

    try:
        NDK_ROOT = os.environ['NDK_ROOT']
    except Exception:
        print "NDK_ROOT not defined. Please define NDK_ROOT in your environment."
        sys.exit(1)

    return NDK_ROOT

def _check_python_bin_env():
    ''' Checking the environment PYTHON_BIN, which will be used for building
    '''

    try:
        PYTHON_BIN = os.environ['PYTHON_BIN']
    except Exception:
        print "PYTHON_BIN not defined, use current python."
        PYTHON_BIN = sys.executable

    return PYTHON_BIN


class CmdError(Exception):
    pass


@contextmanager
def _pushd(newDir):
    previousDir = os.getcwd()
    os.chdir(newDir)
    yield
    os.chdir(previousDir)

def _run_cmd(command):
    ret = subprocess.call(command, shell=True)
    if ret != 0:
        message = "Error running command"
        raise CmdError(message)

def main():

    cur_platform= '??'
    llvm_path = '??'
    ndk_root = _check_ndk_root_env()
    # del the " in the path
    ndk_root = re.sub(r"\"", "", ndk_root)
    python_bin = _check_python_bin_env()

    platform = sys.platform
    if platform == 'win32':
        cur_platform = 'windows'
    elif platform == 'darwin':
        cur_platform = platform
    elif 'linux' in platform:
        cur_platform = 'linux'
    else:
        print 'Your platform is not supported!'
        sys.exit(1)

    if platform == 'win32':
        x86_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm-3.6/prebuilt', '%s' % cur_platform))
        if not os.path.exists(x86_llvm_path):
            x86_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm-3.5/prebuilt', '%s' % cur_platform))
        if not os.path.exists(x86_llvm_path):
            x86_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm/prebuilt', '%s' % cur_platform))
    else:
        x86_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm-3.6/prebuilt', '%s-%s' % (cur_platform, 'x86')))
        if not os.path.exists(x86_llvm_path):
            x86_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm-3.5/prebuilt', '%s-%s' % (cur_platform, 'x86')))
        if not os.path.exists(x86_llvm_path):
            x86_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm/prebuilt', '%s-%s' % (cur_platform, 'x86')))

    x64_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm-3.6/prebuilt', '%s-%s' % (cur_platform, 'x86_64')))
    if not os.path.exists(x64_llvm_path):
        x64_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm-3.5/prebuilt', '%s-%s' % (cur_platform, 'x86_64')))
    if not os.path.exists(x64_llvm_path):
        x64_llvm_path = os.path.abspath(os.path.join(ndk_root, 'toolchains/llvm/prebuilt', '%s-%s' % (cur_platform, 'x86_64')))

    if os.path.isdir(x86_llvm_path):
        llvm_path = x86_llvm_path
    elif os.path.isdir(x64_llvm_path):
        llvm_path = x64_llvm_path
    else:
        print 'llvm toolchain not found!'
        print 'path: %s or path: %s are not valid! ' % (x86_llvm_path, x64_llvm_path)
        sys.exit(1)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    cocos_root = os.path.abspath(project_root)
    creator_root = os.path.abspath(os.path.join(cocos_root, 'cocos/editor-support/creator'))
    jsb_root = os.path.abspath(os.path.join(project_root, 'cocos/scripting/js-bindings'))
    cxx_generator_root = os.path.abspath(os.path.join(project_root, 'tools/bindings-generator'))

    # save config to file
    config = ConfigParser.ConfigParser()
    config.set('DEFAULT', 'androidndkdir', ndk_root)
    config.set('DEFAULT', 'clangllvmdir', llvm_path)
    config.set('DEFAULT', 'creatordir', creator_root)
    config.set('DEFAULT', 'cocosdir', cocos_root)
    config.set('DEFAULT', 'jsbdir', jsb_root)
    config.set('DEFAULT', 'cxxgeneratordir', cxx_generator_root)
    config.set('DEFAULT', 'extra_flags', '')
    
    if '3.' in llvm_path:
        if '3.6' in llvm_path:
            config.set('DEFAULT', 'clang_include', 'lib/clang/3.6/include')
        else:
            config.set('DEFAULT', 'clang_include', 'lib/clang/3.5/include')
    else:
        config.set('DEFAULT', 'clang_include', 'lib64/clang/3.8/include')

    # To fix parse error on windows, we must difine __WCHAR_MAX__ and undefine __MINGW32__ .
    if platform == 'win32':
        config.set('DEFAULT', 'extra_flags', '-D__WCHAR_MAX__=0x7fffffff -U__MINGW32__')

    conf_ini_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'userconf.ini'))

    print 'generating userconf.ini...'
    with open(conf_ini_file, 'w') as configfile:
      config.write(configfile)


    # set proper environment variables
    if 'linux' in platform or platform == 'darwin':
        os.putenv('LD_LIBRARY_PATH', '%s/libclang' % cxx_generator_root)
        print '%s/libclang' % cxx_generator_root
    if platform == 'win32':
        path_env = os.environ['PATH']
        os.putenv('PATH', r'%s;%s\libclang;%s\tools\win32;' % (path_env, cxx_generator_root, cxx_generator_root))

    try:
        tojs_root = '%s/tools/tojs' % project_root
        output_dir = '%s/cocos/scripting/js-bindings/auto' % project_root

        cmd_args = {
                    # 'cocos2dx.ini' : ('cocos2d-x', 'jsb_cocos2dx_auto'), \
                    # 'cocos2dx_audioengine.ini' : ('cocos2dx_audioengine', 'jsb_cocos2dx_audioengine_auto'), \
                    # 'cocos2dx_network.ini' : ('cocos2dx_network', 'jsb_cocos2dx_network_auto'), \
                    # 'cocos2dx_extension.ini' : ('cocos2dx_extension', 'jsb_cocos2dx_extension_auto'), \
                    # 'cocos2dx_ui.ini' : ('cocos2dx_ui', 'jsb_cocos2dx_ui_auto'), \
                    # 'cocos2dx_spine.ini' : ('cocos2dx_spine', 'jsb_cocos2dx_spine_auto'), \
                    'cocos2dx_dragonbones.ini' : ('cocos2dx_dragonbones', 'jsb_cocos2dx_dragonbones_auto'), \
                    # 'cocos2dx_experimental_webView.ini' : ('cocos2dx_experimental_webView', 'jsb_cocos2dx_experimental_webView_auto'), \
                    # 'cocos2dx_experimental_video.ini' : ('cocos2dx_experimental_video', 'jsb_cocos2dx_experimental_video_auto'), \
                    # 'creator.ini': ('creator', 'jsb_creator_auto'),
                    # 'box2d.ini' : ('box2d', 'jsb_box2d_auto'),
                    }
        target = 'spidermonkey'
        generator_py = '%s/generator.py' % cxx_generator_root
        for key in cmd_args.keys():
            args = cmd_args[key]
            cfg = '%s/%s' % (tojs_root, key)
            print 'Generating bindings for %s...' % (key[:-4])
            command = '%s %s %s -s %s -t %s -o %s -n %s' % (python_bin, generator_py, cfg, args[0], target, output_dir, args[1])
            _run_cmd(command)

        # if platform == 'win32':
        #     with _pushd(output_dir):
        #         _run_cmd('dos2unix *')


        custom_cmd_args = {}
        if len(custom_cmd_args) > 0:
            output_dir = '%s/frameworks/custom/auto' % project_root
            for key in custom_cmd_args.keys():
                args = custom_cmd_args[key]
                cfg = '%s/%s' % (tojs_root, key)
                print 'Generating bindings for %s...' % (key[:-4])
                command = '%s %s %s -s %s -t %s -o %s -n %s' % (python_bin, generator_py, cfg, args[0], target, output_dir, args[1])
                _run_cmd(command)
            # if platform == 'win32':
            #     with _pushd(output_dir):
            #         _run_cmd('dos2unix *')

        print '----------------------------------------'
        print 'Generating javascript bindings succeeds.'
        print '----------------------------------------'

    except Exception as e:
        if e.__class__.__name__ == 'CmdError':
            print '-------------------------------------'
            print 'Generating javascript bindings fails.'
            print '-------------------------------------'
            sys.exit(1)
        else:
            raise


# -------------- main --------------
if __name__ == '__main__':
    main()
