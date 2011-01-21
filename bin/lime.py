#!/usr/bin/env python

"""Utilities for common tasks needed to use lime framework.
"""

import optparse
import subprocess
import logging
import sys
import os.path
import zipfile
import re
import shutil
import fileinput
from os.path import join, splitext, split, exists
from shutil import copyfile
from datetime import datetime

if sys.version_info[0]==3:
    from urllib.request import urlretrieve
else :
    from urllib import urlretrieve


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')
basedir = os.path.normpath(basedir)
curdir = os.path.abspath('.')

closure_dir = os.path.join(basedir,'closure')
closure_deps_file = os.path.join(closure_dir,'closure/goog/deps.js')

box2d_dir = os.path.join(basedir,'box2d')

extdir = join(basedir,'bin/external')
compiler_path = os.path.join(extdir,'compiler.jar')
soy_path = os.path.join(extdir,'SoyToJsSrcCompiler.jar')
projects_path = join(basedir,'bin/projects')

# zipfile.extract & os.path.relpath missing in 2.5
if sys.version_info < (2,6):
    print("Error. Python 2.6+ is required")
    sys.exit(1)

def removeDupes(seq):
    # Not order preserving
    keys = {}
    for e in seq:
        keys[e.rstrip()] = 1
    return keys.keys()
    
def makeProjectPaths(add):
    lines = open(projects_path,'r').readlines()
    if len(add):
        lines.append(add)
    newlines = filter(lambda x: exists(join(basedir,x.rstrip())) and len(x.rstrip()),lines)
    newlines = removeDupes(newlines)
    
    f = open(projects_path,'w')
    f.write('\n'.join(newlines))
    f.close()

def rephook(a,b,c):
    sys.stdout.write("\r%2d%%" % ((100*a*b)/c) )
    sys.stdout.flush()

def checkDependencies():
    
    #Check git
    retcode = subprocess.Popen(subprocess.list2cmdline(["git","--version"]), stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True).wait()
    if retcode!=0:
        logging.error('Lime requires git. Get it from http://git-scm.com/download')
        sys.exit(1) 
    
    
    #Closure Library
    if not (os.path.exists(closure_dir) and  os.path.exists(closure_deps_file)):
        print ('Closure Library not found. Downloading to %s' % closure_dir)
        print ('Please wait...')
        
        retcode = subprocess.Popen(subprocess.list2cmdline(["git","svn","clone","-r","HEAD","http://closure-library.googlecode.com/svn/trunk/",closure_dir]),shell=True).wait()
        
        if(retcode!=0):
            #try pure svn
            retcode = subprocess.Popen(subprocess.list2cmdline(["svn","checkout","http://closure-library.googlecode.com/svn/trunk/",closure_dir]),shell=True).wait()
            
            if(retcode!=0):
                logging.error('Error while downloading Closure Library. Discontinuing.')
                sys.exit(1)
    
    
    #Box2D
    if not os.path.exists(box2d_dir):
        print ('Box2DJS not found. Downloading to %s' % box2d_dir)
        print ('Please wait...')
        
        retcode = subprocess.Popen(subprocess.list2cmdline(["git","clone","http://github.com/thinkpixellab/box2d.git",box2d_dir]),shell=True).wait()
        
        if(retcode!=0):
            logging.error('Error while downloading Box2D. Discontinuing.')
            sys.exit(1)
    
    #External tools dir
    if not os.path.exists(extdir):
        os.mkdir(extdir)
    
    #Closure compiler
    if not os.path.exists(compiler_path):
        zip_path = os.path.join(extdir,'compiler.zip')
        print ('Downloading Closure Compiler: ')
        urlretrieve("http://closure-compiler.googlecode.com/files/compiler-latest.zip",zip_path,rephook)
        print ('\nUnzipping...')
        zippedFile = zipfile.ZipFile(zip_path)
        zippedFile.extract('compiler.jar',extdir)
        zippedFile.close()
        print ('Cleanup')
        os.unlink(zip_path)
    
    
    #Closure Templates
    if not os.path.exists(soy_path):
        zip_path = os.path.join(extdir,'soy.zip')
        print ('Downloading Closure Templates(Soy):')
        urlretrieve("http://closure-templates.googlecode.com/files/closure-templates-for-javascript-latest.zip",
            zip_path,rephook)
        print ('\nUnzipping...')
        zippedFile = zipfile.ZipFile(zip_path)
        zippedFile.extract('SoyToJsSrcCompiler.jar',extdir)
        zippedFile.close()
        print ('Cleanup')
        os.unlink(zip_path)
    
    if not os.path.exists(projects_path):
        open(projects_path,'w').close()
    
    makeProjectPaths('')
    
    
    
def update():
    
    reldir = os.path.relpath(curdir,basedir)
    if reldir!='.':
        makeProjectPaths(reldir)
    
    print ('Updating Closure deps file')
    
    paths = open(projects_path,'r').readlines()
    paths.append('lime\n')
    paths.append('box2d\n')
    
    opt = ' '.join(map(lambda x: '--root_with_prefix="'+os.path.join(basedir,x.rstrip())+'/ ../../../'+x.rstrip()+'/"',paths))

    call = os.path.join(closure_dir,'closure/bin/build/depswriter.py')+' --root_with_prefix="'+\
        closure_dir+'/ ../../" '+opt+' > '+closure_deps_file
        
    print (call)
    
    subprocess.call(call,shell=True)
    

def create(name):
    
    path = os.path.join(curdir,name)
    
    if exists(path):
        logging.error('Directory already exists: %s',path)
        sys.exit(1) 
    
    name = os.path.basename(path)
    
    proj = os.path.relpath(path,basedir)
    
    if proj!='.':
        makeProjectPaths(os.path.relpath(path,basedir))
    
    shutil.copytree(os.path.join(basedir,'lime/templates/default'),path)
    
    for root, dirs, files in os.walk(path):
        for fname in files:
            newname = fname.replace('__name__',name)
            if fname.find("__name__")!=-1:
                os.rename(os.path.join(path,fname),os.path.join(path,newname))
            for line in fileinput.FileInput(os.path.join(path,newname),inplace=1):
                line = line.replace('{name}',name)
                print (line,)
            
    print ('Created %s' % path)
    
    update()


def genSoy(path):
    
    if not os.path.exists(path):
        logging.error('No such directory %s',path)
        exit(1)
        
    for root,dirs,files in os.walk(path):
        for fname in files:
            if fname[-4:]=='.soy':
                soypath = os.path.join(root,fname)
                call = "java -jar "+soy_path+" --cssHandlingScheme goog --shouldProvideRequireSoyNamespaces --outputPathFormat "+soypath+".js "+soypath;
                print (call)
                subprocess.call(call,shell=True)

def build(name,options):
    
    dir_list = open(projects_path,'r').readlines()
    dir_list.append('lime')
    dir_list.append('box2d')
    dir_list.append('closure')
    
    #dir_list = filter(lambda x: os.path.isdir(os.path.join(basedir,x)) and ['.git','bin','docs'].count(x)==0 ,os.listdir(basedir))

    opt = ' '.join(map(lambda x: '--root="'+os.path.join(basedir,x.rstrip())+'/"',dir_list))
    
    call = os.path.join(closure_dir,'closure/bin/build/closurebuilder.py')+' '+opt+' --namespace="'+name+'" '+\
        '-o compiled -c '+compiler_path;
    
    
    if options.advanced:
        call+=" -f --compilation_level=ADVANCED_OPTIMIZATIONS"
        
    if options.map_file:
        call+=" -f --formatting=PRETTY_PRINT -f --create_source_map="+options.map_file
    else:
        call+=" -f --define='goog.DEBUG=false'"
        
    outname = options.output    
        
    if options.output:
        if options.output[-3:] == '.js':
            outname = options.output[:-3]
        call+=" > "+outname+'.js'
        if not exists(os.path.dirname(outname)):
            os.makedirs(os.path.dirname(outname))
        
    
    subprocess.call(call,shell=True);
    
    if options.output and options.preload:
        name = os.path.basename(outname)
        target = os.path.dirname(outname)
        source = os.path.join(basedir,'lime/templates/preloader')

        for root, dirs, files in os.walk(source):
            
            for fname in files:
                from_ = join(root, fname)           
                to_ = from_.replace(source, target, 1)
                to_directory = split(to_)[0]
                to_ = to_.replace('__name__',name)
                if not exists(to_directory):
                    os.makedirs(to_directory)
                if not exists(to_):
                    copyfile(from_, to_)
        
        for root, dirs, files in os.walk(target):

            for fname in files:         
                if exists(os.path.join(target,fname)):
                    for line in fileinput.FileInput(os.path.join(target,fname),inplace=1):
                        line = line.replace('{name}',name)
                        line = line.replace('{callback}',options.preload)
                    
                        if fname == name+'.manifest':
                            line = re.sub(r'# Updated on:.*','# Updated on: '+datetime.now().strftime("%Y-%m-%d %H:%M:%S"),line)
                        print (line,)
        
    

def main():
    """The entrypoint for this script."""
    
    usage = """usage: %prog [command] [options]
Commands:
    init            Check lime dependecies and setup if needed
    update          Update Closure dependency file. Need to run every time you 
                    change goog.provide() or goog.require()
    create [path/name]   Setup new project [name]
    gensoy [path]   Convert all *.soy files under path to *.soy.js files
    build [name]    Compile project to single Javascript file"""
    parser = optparse.OptionParser(usage)
    
    parser.add_option("-a", "--advanced", dest="advanced", action="store_true",
                      help="Build uses ADVANCED_OPTIMIZATIONS mode (encouraged)")
    parser.add_option("-o", "--output", dest="output", action="store", type="string",
                      help="Output file for build result")
    
    parser.add_option("-m", "--map", dest="map_file", action="store",
                      help="Build result sourcemap for debugging. Also turns on pretty print.")
                      
    parser.add_option("-p", "--preload", dest="preload", action="store", type="string",
                        help="Generate preloader code with given callback as start point.")
    
    (options, args) = parser.parse_args()
    if not (len(args) == 2 or (len(args)==1 and ['init','update'].count(args[0])==1 )) :
        parser.error('incorrect number of arguments')
    
    checkDependencies()
    
    if args[0]=='init' or args[0]=='update':
        update()
    
    elif args[0]=='create':
        create(args[1])
        
    elif args[0]=='gensoy':
        genSoy(args[1])
        
    elif args[0]=='build':
        build(args[1],options)    
        
    else:
        logging.error('No such command: %s',args[0])
        exit(1)
    
if __name__ == '__main__':
    main()
