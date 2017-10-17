#!/usr/bin/env python
# -*- coding: utf8 -*-
#####################################################
#   随身考勤机原型
#  设计者   蒋宁
#####################################################
import binascii
import time
import RPi.GPIO as GPIO
import signal
import serial
from time import sleep
import os
import datetime
import Image
import ILI9341 as TFT
import Adafruit_GPIO.SPI as SPI
import ImageFont
import ImageDraw
import subprocess
import sqlite3					#导入sqlite3模块，树莓派操作系统内置的，无需安装
import MFRC522					#导入SPI  MFRC522读卡器模块
def end_read(signal,frame):		#MFRC522 读卡相关函数
	global continue_reading
	continue_reading = False

#导入自动生成UID二维码的函数，请首先安装：pip install qrcode
import qrcode
#生成二维码图片的函数
def make_qr(str,save):
	qr=qrcode.QRCode(
		version=4,  #生成二维码尺寸的大小 1-40  1:21*21（21+(n-1)*4）
		error_correction=qrcode.constants.ERROR_CORRECT_M, #L:7% M:15% Q:25% H:30%
		box_size=8, #每个格子的像素大小
		border=2, 	#边框的格子宽度大小
	)
	qr.add_data(str)
	qr.make(fit=True)
	img=qr.make_image()
	img.save(save)

#生成带logo的二维码图片的函数
def make_logo_qr(str,logo,save):
	#参数配置
	qr=qrcode.QRCode(
		version=4,
		error_correction=qrcode.constants.ERROR_CORRECT_M,
		box_size=8,
		border=2,
	)
	#添加内容
	qr.add_data(str)
	#
	qr.make(fit=True)
	#生成二维码
	img=qr.make_image()
	#
	img=img.convert("RGBA")
 
	#添加logo
	if logo and os.path.exists(logo):
		icon=Image.open(logo)
		#获取二维码图片的大小
		img_w,img_h=img.size
 
		factor=4
		size_w=int(img_w/factor)
		size_h=int(img_h/factor)
 
		#logo图片的大小不能超过二维码图片的1/4
		icon_w,icon_h=icon.size
		if icon_w>size_w:
			icon_w=size_w
		if icon_h>size_h:
			icon_h=size_h
		icon=icon.resize((icon_w,icon_h),Image.ANTIALIAS)
		#详见：http://pillow.readthedocs.org/handbook/tutorial.html
 
		#计算logo在二维码图中的位置
		w=int((img_w-icon_w)/2)
		h=int((img_h-icon_h)/2)
		icon=icon.convert("RGBA")
		img.paste(icon,(w,h),icon)
		#详见：http://pillow.readthedocs.org/reference/Image.html#PIL.Image.Image.paste
 
	#保存处理后图片
	img.save(save)

#显示屏SPI接口参数	
DC = 3		#18
RST = 25	#23
SPI_PORT = 0
SPI_DEVICE = 0
#显示屏初始设置
nu=1
x=0
y=0
r=10
g=250
b=200
jd=270
width=240
height=320
backcolor=[(0,0,0)]
backdata=backcolor*(width*height)
# 显示屏函数类Create TFT LCD display class.
disp = TFT.ILI9341(DC, rst=RST, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=64000000))
# 初始化显示屏Initialize display.
disp.begin()
# 调入字体.
font = ImageFont.truetype('simhei.ttf', 24)
# 显示屏清屏函数
def clear(disp,backdata):
	disp.buffer.putdata(backdata)
# 显示屏清屏函数调用方法
#clear(disp,backdata)
# 创建可旋转显示文字的函数。
def draw_rotated_text(image, text, position, angle, font, fill=(255,255,255)):
	text = text.decode('utf-8')	                                # 转换字符编码.
	draw = ImageDraw.Draw(image)	                            # 获取渲染字体的宽度和高度.
	width, height = draw.textsize(text, font=font)
	textimage = Image.new('RGBA', (width, height), (0,0,0,0))	# 创建一个透明背景的图像来存储文字.
	textdraw = ImageDraw.Draw(textimage)	                    # 渲染文字.
	textdraw.text((0,0), text, font=font, fill=fill)
	rotated = textimage.rotate(angle, expand=1)	                # 旋转文字图片.
	image.paste(rotated, position, rotated)	                    # 把文字粘贴到图像，作为透明遮罩.
# 获取IP地址函数
def myip():
	arg='ip route list' 
	p=subprocess.Popen(arg,shell=True,stdout=subprocess.PIPE) 
	data = p.communicate() 
	split_data = data[0].split() 
	ipaddr = split_data[split_data.index('src')+1]
	print "IP:",ipaddr
	return ipaddr
# RFID卡读写函数
def rwcard(c):
#	sleep(1)
	uid=ser2.write(c.decode('hex'))                  
	uid=ser2.read(64)#            
	return uid

# 蜂鸣器定义
def buzz(i):
	GPIO.setmode(GPIO.BCM) #BOARD)  
	GPIO.setup(27, GPIO.OUT)  #13
	j=1
	while j<(i+1):
		GPIO.output(27, GPIO.HIGH)  
		time.sleep(0.1)  
		GPIO.output(27, GPIO.LOW)  
		time.sleep(0.1)
		j=j+1
# 指示灯定义
def led(i,j):
	if i>2:
		l=18
	elif i==1:
		l=18
	elif i==2:
		l=17
	GPIO.setmode(GPIO.BCM)  
	GPIO.setup(l, GPIO.OUT)  
	if j==1:
		GPIO.output(l, GPIO.HIGH)  
	else:  
		GPIO.output(l, GPIO.LOW) 
# 定义串口（TX800BT、JSC260、同方微电子3060等需要）
#ser1 = serial.Serial("/dev/ttyUSB0", baudrate=2400,parity=serial.PARITY_EVEN,bytesize=8,stopbits=1, timeout=1)
ser2 = serial.Serial("/dev/ttyUSB0", baudrate=9600,parity=serial.PARITY_NONE,bytesize=8,stopbits=1, timeout=1)

# 程序运行开始
print "测试程序启动中......"
# 获取IP地址
ipaddr=myip()
print "正在自动识别读卡器..."
######自动识别读卡器
cpudkq="TX800BT"
while cpudkq=="":                   
# 尝试TX800BT读卡器
	c="20004f00b003"                      
	cpudkq=rwcard(c)
	cpudkq=binascii.b2a_hex(cpudkq)
#	print cpudkq[0:18]
#                     2000000a5458383030207003ae142803
	if cpudkq[0:18]=="2000000a5458383030":
		print "读卡器名称=TX800BT"
		cpudkq="TX800BT"
		break
# 尝试清华同方THM3060读卡器
	ser2 = serial.Serial("/dev/ttyUSB0", baudrate=115200,parity=serial.PARITY_NONE,bytesize=8,stopbits=1, timeout=1)
	c="c050610\n"						#清华同方THM3060直接读卡指令
	cpudkq=""
	cpudkq=ser2.write(c)                 
	cpudkq=ser2.read(64)
#	print "探测读卡器型号返回数据：",cpudkq
	if c in cpudkq:
		print "读卡器名称=THM3060"
		cpudkq="THM3060"
		break
# 尝试JSC260读卡器
	ser2 = serial.Serial("/dev/ttyUSB0", baudrate=9600,parity=serial.PARITY_NONE,bytesize=8,stopbits=1, timeout=1)
	c="JSC0004C1C1"                    #大卡cpu方式寻卡指令
	cpudkq=""
	cpudkq=ser2.write(c)                  
	cpudkq=ser2.read(64)            
	print cpudkq
	if cpudkq[0:3]=="JSC":
		print "读卡器名称=JSC260"
		cpudkq="JSC260"
		break
# 否则是MFRC522读卡器
	else:
		print "读卡器名称=MFRC522"
		cpudkq="MFRC522"
		import MFRC522                	#导入SPI  MFRC522读卡器模块
		def end_read(signal,frame):
			global continue_reading
			continue_reading = False
		break
print "读卡器模块：",cpudkq


# 清屏并且显示欢迎词
clear(disp,backdata)
draw_rotated_text(disp.buffer,"庚商实验室管理系统", (124, 32), jd, font, fill=(r,g,b))
draw_rotated_text(disp.buffer,"随身考勤智能终端测试", (100, 30), jd, font, fill=(r,g,b))
#draw_rotated_text(disp.buffer,"IP地址:"+ipaddr, (60, 20), jd, font, fill=(0,255,0))
disp.display()
sleep(2)
print "开始自动循环测试..."
print "+++++++++++++++++++++++++++++++++"
tim1=datetime.datetime.now()
nx=1	#循环测试次数
while 1==1:
	clear(disp,backdata)
	draw_rotated_text(disp.buffer,"庚商随身考勤智能终端", (214, 30), jd, font, fill=(r,g,b))
	draw_rotated_text(disp.buffer,"请刷卡！等待中。。。", (128, 24), jd, font, fill=(200,g,b)) #请刷卡
	disp.display()
# 读卡环节-指定读卡方式
	kaleix="auto"
# 读卡环节-读卡器及指令选择
# THM卡读写指令，每个指令后面需要添加换行符
	c1="c05060401\n"				#直接读取15693 UID
	c2="c05060501\n"				#直接读取type A UID  
	c3="c05060601\n"				#直接读取type B UID  
	c4="c05060101\n"				#type B 开场
	c5="c05060102\n"				#type A 开场  
	c6="c05060103\n"				#15693 开场  
	c7="c050602\n"					#关场  
	c8="c050901\n"					#波特率  
	c9="b\n"						#蜂鸣器指示灯  
	c10="a\n"						#启动自动读卡
	c11="s\n"						#退出自动读卡状态 
	c12="c050b12345678\n"			#设置模块序列号  
	c13="c050a\n"					#读取模块序列号  
	c14="f52\n"						#对TYPE A类型PICC进行wake up（唤醒）操作，PICC返回ATQA  52：ALL
	c15="f26\n"						#对TYPE A类型PICC进行wake up（唤醒）操作，PICC返回ATQA  26：idle
	c16="f050000\n"					#对TYPE B类型PICC进行wake up（唤醒）操作，PICC返回ATQB   
	c17="f260100\n"					#对15963 类型PICC进行wake up（唤醒）操作，PICC返回inventory  
	c18="f9320\n"					#对TYPE A类型读取UID 操作，先f26后f9320
	c19="f9370\n"					#对TYPE B类型读取UID 先f26后f9320+UID
	c20="c05060e\n"					#对TYPE A类型读取UID 操作，单指令可读4、7字节UID，逗号分隔，有缺陷。
	c21="c050610\n"					#对TYPE A类型读取UID 操作，单指令可读4、7字节UID，逗号分隔。
# 进入读卡操作
	uid=""
#####TX800BT小卡读卡操作
	if cpudkq=="TX800BT" and kaleix=="cpu":  #小卡CPU方式读卡号
		c="20002D00D203"                     #小卡CPU卡协议停活—TX_CPUDeselect 退出读卡状态  
		uid=binascii.b2a_hex(rwcard(c))                  
		c="2000220101DD03"                   #小卡CPU卡复合指令复位—TX_CPUActiveEnter激活并且读卡号 
		uid=binascii.b2a_hex(rwcard(c))                  
#		print "读卡原始数据：",str(uid)
	elif cpudkq=="TX800BT" and kaleix=="auto": #小卡自动方式读卡号
		while uid=="":
			uid=binascii.b2a_hex(ser2.read(64))#小卡自动方式只读卡号
#		print "读卡原始数据：",str(uid)
	elif cpudkq=="TX800BT" and kaleix=="M1": #小卡M1方式读取卡号
		c="20005200ad03"                     #小卡M1方式配置—TX_Config 
		uid=binascii.b2a_hex(rwcard(c))                  
		c="2000100100ee03"                   #小卡M1方式读卡号TX_GetCardSnr指令
		uid=""
		while uid=="":
			uid=binascii.b2a_hex(rwcard(c))
#		print "读卡原始数据：",str(uid)

#####  JSC260大卡读卡操作
	elif cpudkq=="JSC260" and kaleix=="cpu": #大卡cpu方式读取卡号
		c="JSC0004C1C1"                      #大卡cpu方式寻卡指令
		uid=ser2.write(c)                  
		uid=ser2.read(64)            
#		print "寻卡原始数据：",str(uid)
		c=("JSC0004C0C0")                    #大卡TypeA/TypeB CPU卡寻卡指令（此命令寻卡后，防冲撞指令失效），读卡号 
		uid=ser2.write(c)            
		uid=ser2.read(64)            
#		print "读卡原始数据：",str(uid)
	elif cpudkq=="JSC260" and kaleix=="M1":	#大卡M1方式读取卡号
#		c="JSC0004C1C1"						#大卡TypeA CPU 卡上电复位指令（可读社保卡、白卡、钥匙圈卡，东华校园卡有困难）
		c="JSC0004B2B2"						#大卡M1方式寻卡指令（可读东华大学校园卡、白卡、钥匙圈卡）
		uid=ser2.write(c)					#大卡寻卡请求
		uid=ser2.read(64)					#大卡寻卡结果
		print "寻卡原始数据：",str(uid)
		c="JSC0004B3B3"              		#大卡M1方式读M1卡号（防冲撞）指令
		uid=ser2.write(c)            		#大卡读M1卡号请求
		uid=ser2.read(64)            		#大卡读M1卡号读取
		print "读卡原始数据：",str(uid)

#####  同方微电子THM3060卡读卡操作
	elif cpudkq=="THM3060" and kaleix=="M1":  	#同方卡M1方式读取卡号
# 同方M1（Type A）卡一指令（c050610）万能读取卡号（普通M1、社保、银行、公交、校园、敬老卡）
		uid=""
		while uid=="":							#确保读到数据
			uid=ser2.write("c050610\n")        	#Type A方式万能读取UID指令（可读各种卡）
			uid=ser2.read(196)					
#			print "读卡原始数据：",uid
		uid=uid.replace("\n","")			#去掉换行
		uid=uid.replace("\r","")			#去掉回车
		uid=uid.strip()						#去掉回传的多余空格
		print "无换行原始数据：",uid
		np1=uid.index("UID")				#定位UID位置
		uid=uid[np1+7:]						#截取有效数据
#		print "UID长度：",len(uid)
		if len(uid)>8:						#c050602RF carrier off!c050610UID :  1DD21A0D590000
			uid=uid[12:]+uid[10:12]+uid[8:10]+uid[6:8]+uid[4:6]+uid[2:4]+uid[0:2]
			kalx="UltraLight卡号："			#给定卡类型
		elif len(uid)<2:					#无卡的数据：c050610UID : 0;
			kalx="无卡"
		else:								#c050602RF carrier off!c050610UID :  D6C254C9
			kalx="通用M1卡号："				#给定卡类型
			uid=uid[6:]+uid[4:6]+uid[2:4]+uid[0:2]
#		print "读卡卡号数据：",uid
		if "TYPE A Read CARD fault!" in uid:uid="无卡，请放上有效ID卡在下一循环继续测试！"#
		ser2.write(c7)                 			#读卡关场                 
# 同方卡cpu（Type B）直接方式读卡号（身份证）
	elif cpudkq=="THM3060" and kaleix=="cpu":  	#同方卡cpu（TYPE B）方式读取卡号
		c=c3              						#同方卡cpu（TYPE B）方式直接读取卡指令"c05060601\n"（可读身份证）
		ser2.write(c4)							#TYPE B读卡开场       
		uid=""
		while uid=="":
			uid=ser2.write(c)        			#同方卡读卡号请求    
			uid=ser2.read(196)        			#同方卡读卡号读取    
#			print "读卡原始数据：",str(uid)
			uid=uid.replace("\n","")			#去掉换行
			uid=uid.replace("\r","")			#去掉回车
			uid=uid.strip()						#去掉回传的多余空格
#			print "读卡无换行换行原始数据：",str(uid)
			if "UID:" in uid:
				np1=uid.index("UID:")			#定位UID位置
				uid=uid[np1+4:np1+20]			#取出8字节UID数据
				uid=uid[7]+uid[6]+uid[5]+uid[4]+uid[3]+uid[2]+uid[1]+uid[0]
#			print "读卡处理后数据：",str(uid)
		if "TYPE A Read CARD fault!" in uid:uid="无卡，请放上有效ID卡在下一循环继续测试！"#
		ser2.write(c7)                 			#读卡关场
		
#####  SPI RC522读取M1卡操作
	elif cpudkq=="MFRC522":          
		signal.signal(signal.SIGINT, end_read)
		MIFAREReader = MFRC522.MFRC522()
		uid=""
		while uid=="":
			(status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
			if status == MIFAREReader.MI_OK:
				(status,uid) = MIFAREReader.MFRC522_Anticoll()
			if status == MIFAREReader.MI_OK:
				uid=str(hex(uid[3]))[2:]+str(hex(uid[2]))[2:]+str(hex(uid[1]))[2:]+str(hex(uid[0]))[2:]
				break
			else:uid=""
#			print "用户M1卡号: "+uid
	uid=str(uid)
#	print "卡号：",uid

#  读卡数据处理环节
	if (cpudkq<>"MFRC522" and cpudkq<>"THM3060") and len(uid)<10:		#读卡失败处理
		buzz(4)
		draw_rotated_text(disp.buffer,"读卡失败，请检查读卡器链路！", (0, 0), jd, font, fill=(255,0,0))
		disp.display()
		print cpudkq+"读卡失败，请检查读卡器链路！：",uid
		break
#####小卡读卡数据处理  
#  d78c93204d                      						#小卡自动方式读取卡号数据
	elif cpudkq=="TX800BT" and kaleix=="auto":          #小卡自动方式读取卡号数据处理
		print uid
		uuid=uid[-4:-2]+uid[-6:-4]+uid[-8:-6]+uid[-10:-8]
		kalx="自动读取："
#  2000000804005304d78c93204d03                      	#小卡M1方式读取M1 S50样品公交卡卡号数据
	elif uid[0:16]=="2001000804005304":          		#小卡读取M1卡数据处理
		uuid=uid[-6:-4]+uid[-8:-6]+uid[-10:-8]+uid[-12:-10]
		kalx="公交卡号："
#  2000000b440000071dd21a0d4800013703                	#小卡M1方式读取Mifare UltraLight社保卡号数据
	elif uid[0:16]=="2000000b44000007":                	#小卡读取社保卡数据处理
		uuid=uid[-6:-4]+uid[-8:-6]+uid[-10:-8]+uid[-12:-10]+uid[-14:-12]+uid[-16:-14]+uid[-18:-16]
		kalx="MUL社保卡号："
#  2000000804002804f651fab33103                       	#小卡M1方式读取东华校园卡数据
	elif uid[0:16]=="2000000804002804":                 #小卡M1方式读取东华校园卡数据处理
		uuid=uid[-6:-4]+uid[-8:-6]+uid[-10:-8]+uid[-12:-10]
		kalx="东华校园卡M1号："
	elif uid[0:16]=="2000000804000804":                 #小卡M1方式读取M1白卡数据处理
		uuid=uid[-6:-4]+uid[-8:-6]+uid[-10:-8]+uid[-12:-10]
		kalx="M1白卡号："
#  200000080800200494698a897503                       	#小卡M1方式读取银行卡号数据
	elif uid[0:16]=="2001000808002004":                 #小卡M1方式读取银行卡号数据处理
		uuid=uid[-6:-4]+uid[-8:-6]+uid[-10:-8]+uid[-12:-10]
		kalx="银行卡号："                                
#  2000000f0e7733a00286884748f2346698a70004503       	#小卡cpu方式读取银行卡号数据处理
	elif uid[0:26]=="2000000f0e7733a00286884748":       #小卡cpu方式读取银行卡号数据处理
#		a1=uid[-8:-6]+uid[-10:-8]+uid[-12:-10]
#		a2=uid[-12:-10]+uid[-14:-12]+uid[-16:-14]
		uuid=uid[-16:-6]								#10字节str(int(a1,16))+str(int(a2,16))
		kalx="银行卡号："                                
#  20000015147880800200004a301386454a5522204334301097a003   #小卡cpu方式读敬老卡样品数据
	elif uid[0:26]=="20000015147880800200004a30":           #小卡cpu方式读敬老卡样品卡号数据处理
#		a1=uid[-8:-6]+uid[-10:-8]+uid[-12:-10]
#		a2=uid[-12:-10]+uid[-14:-12]+uid[-16:-14]
		uuid=uid[-16:-6]									#10字节str(int(a1,16))+str(int(a2,16))
		kalx="敬老卡号："                                
#  20000011107880a00220900000000000d6c254c9009d03      	#小卡cpu方式读取校园卡数据
	elif uid[0:16]=="20000011107880a0":                	#小卡cpu方式读取校园卡数据处理
#		a1=uid[-8:-6]+uid[-10:-8]
#		a2=uid[-12:-10]+uid[-14:-12]
		uuid=uid[-14:-6]								#10字节 str(int(a1,16))+str(int(a2,16))
		kalx="东华校园卡cpu号："

#####大卡读卡数据处理
# JSC000E0041D6C254C9C8                     	#大卡CPU方式读东华校园卡数据
	elif uid[0:9]=="JSC000E00":               	#大卡CPU方式读东华校园卡数据处理
		uuid=uid[-4:-2]+uid[-6:-4]+uid[-8:-6]+uid[-10:-8]
		kalx="东华校园卡cpu号："
# JSC000C00D6C254C989                       	#大卡M1方式读东华校园卡卡数据
# JSC000C00FBC3192B0A                       	#大卡M1方式读白卡数据
	elif uid[0:9]=="JSC000C00":               	#大卡M1方式读M1卡数据处理
		uuid=uid[-4:-2]+uid[-6:-4]+uid[-8:-6]+uid[-10:-8]
		kalx="普通卡M1号："
# JSC0012001DD21A4D89000081                 	#大卡M1方式读社保卡数据
	elif uid[0:9]=="JSC001200":               	#大卡M1方式读社保卡数据处理
		uuid=uid[-4:-2]+uid[-6:-4]+uid[-8:-6]+uid[-10:-8]+uid[-12:-10]+uid[-14:-12]+uid[-16:-14]
		kalx="社保卡M1号："
#####THM3060读卡数据处理
	elif cpudkq=="THM3060" and kaleix=="M1" and len(uid)<22:	#THM3060M1方式读取TYPE A卡数据处理
		uuid=uid												#无处理 str(int(a1,16))+str(int(a2,16))
#		kalx="THM3060读TYPE A卡号："
	elif cpudkq=="THM3060" and kaleix=="cpu" and len(uid)<22:	#THM3060M1方式读取TAPE B卡数据处理
		uuid=uid												#无处理 [0:16]#str(int(a1,16))+str(int(a2,16))
		kalx="TYPE B卡号："
#####MFRC522读卡数据处理
###########################################校园卡数据：[214, 194, 84, 201, 137]  社保卡数据：[136, 29, 210, 26, 93]
###########################################  白卡数据：[144, 198, 252, 121, 211]
	elif cpudkq=="MFRC522" and uid<>"":                
		uuid=uid										#无处理
		kalx="用户M1卡号："
#####无卡或不兼容卡数据处理
	else:												#无卡或不兼容卡数据处理
		uuid="无卡或不兼容卡"
		kalx="用户卡号："
	print cpudkq+"读"+kalx,uuid
	if 1==1:      #uuid=="432289763041":	             #判断卡号是否有效
		buzz(1)
		tim2=tim1
		tim=datetime.datetime.now() #获取时间
		tim1=tim
		timejg=str(tim1-tim2)[-9:-5]
#		print str(timejg)
		tim=tim.strftime("%F-%T")
		print str(nx)+"次",tim,"间隔:"+timejg+"秒"
#		sleep(5)
#	print uuid
##### 生成注册地址+uuid参数的二维码图片
	save_path='theqrcode.jpg'	#指定生成后保存的文件名
	logo='gs.jpg'				#logo图
	str0="https://cas.gvsun.net:8443/cas/login"+"?uid="+uuid
	#make_qr(str0)						#生成普通二维码
	make_logo_qr(str0,logo,save_path)	#生成带LOGO二维码

#######################################
#   数据库处理环节
#--------------------------------------
# sskq.db is a file in the working directory.
	conn = sqlite3.connect("sskq.db")	# 连接一个数据库，如果没有则自动创建一个
	conn.text_factory=str				# 定义表中文本属性
	c = conn.cursor()					# 定义一个光标指针
# 删除一个数据表
#	conn.execute('DROP TABLE xuesen')
# 创建一个数据表xuesen:（括号内是字段及字段属性：NULL: 表示该值为NULL值。INTEGER: 无符号整型值。REAL: 浮点值。TEXT: 文本字符串，存储使用的编码方式为UTF-8、UTF-16BE、UTF-16LE。BLOB: 存储Blob数据，该类型数据和输入数据完全相同。）
	conn.execute("CREATE TABLE IF NOT EXISTS xuesen(xuehao text, uid text, name text)")
# 保存改变
	conn.commit()
# 关闭数据库连接
	conn.close()
	conn = sqlite3.connect("sskq.db")
	conn.text_factory=str
	c    = conn.cursor()
	xm1=u"王麻子"
	xm2=u"张小明"
	xm3=u"刘加满"
# 插入一些记录调试用
#	for t in[("2017090001", "d6c254c9", xm1),("2017090003", "a6c254c9",xm2),]:       #("2017090004", "100002", xm3)]:
#		conn.execute("insert into xuesen values (?,?,?)", t)
#	conn.commit()
# 检索数据库查找符合某些条件的记录
#	c.execute('select * from xuesen')# where book.category=1')
#	j=c.fetchone()	#将该记录的各字段数据存入一个数组							
#	print j
#	if "d6c254c9" in j:print "OK"

# 删除记录
#	conn.execute("delete from xuesen")  # 删除xuesen表里的全部记录  
#	conn.commit() 
	
	c.execute('select * from xuesen')	# 选定数据表的全部记录
	sjk=(c.fetchall())					# 把数据表全部记录读入一个数组列表
#	print sjk
	total=len(sjk)						# 获取数据表记录的数目（列表的行数）
	print "原有记录数:",total

# 检查刚刚刷卡的UID是否已经存在于数据表中
	bj="y"
	n=0
	c.execute("select * from xuesen") 	
	while n<total:						# 逐条核对
		j=c.fetchone()
#		print n,"=====",j[1],uuid
		if uuid == str(j[1]) and str(j[0])!="":		# 如果UID在库中并且已经注册，设置通过认证标志ok，退出核对
			bj="ok"
			print str(j[2])+"同学身份认证通过！"
			clear(disp,backdata)
			draw_rotated_text(disp.buffer,str(j[2])+"同学，你好！", (200, 0), jd, font, fill=(r,g,b))	#显示学生姓名卡号
			draw_rotated_text(disp.buffer,"学号："+str(j[0]), (176, 0), jd, font, fill=(r,g,b))        	#显示学号
			draw_rotated_text(disp.buffer,"考勤时间:", (152, 0), jd, font, fill=(r,g,b))        		#显示考勤
			draw_rotated_text(disp.buffer,str(tim1), (128, 0), jd, font, fill=(r,g,b))        			#显示考勤时间
			disp.display()
			sleep(5)
#			print "逐行:",bj
			break
		elif uuid == str(j[1]) and str(j[0])=="":	# 如果UID在库中但是没有注册，设置请注册标志qzc，退出核对
			bj="qzc"
			print uuid+"尚未注册！"
			clear(disp,backdata)
			draw_rotated_text(disp.buffer,uuid+"新同学，欢迎您！", (200, 0), jd, font, fill=(r,g,b))	#显示UID及欢迎词
			draw_rotated_text(disp.buffer,"请扫描二维码进行注册！：", (176, 0), jd, font, fill=(r,g,b))	#提示注册及方法
			draw_rotated_text(disp.buffer,"需要您输入学号和姓名", (152, 0), jd, font, fill=(r,g,b))      
			draw_rotated_text(disp.buffer,"根据提示刷校园卡确认", (128, 0), jd, font, fill=(r,g,b))     
			draw_rotated_text(disp.buffer,"当前记录数："+str(total), (104, 0), jd, font, fill=(r,g,b))		#显示当前数据库记录数
			disp.display()
# 显示公司LOGO及注册地址二维码
			clear(disp,backdata)
			image = Image.open('theqrcode.jpg')
			image = image.rotate(270).resize((120, 120))
			disp.dispimg(image)
			sleep(10)
#			print "逐行:",bj
			break
		else:bj="y"				# 否则设置允许添加记录标志：y
		n+=1
#	print "最后检索标志：",bj	# 决定是否添加新刷卡的UID记录
	conn.close()
	conn = sqlite3.connect("sskq.db")
	conn.text_factory=str
	c    = conn.cursor()

	if bj=="y" or total==0:		# 如果数据表中无记录或没有此UID，插入一条记录。
		print uuid+"尚未入库！将添加新记录"
		for t in[("", uuid, ""),]:
			conn.execute("insert into xuesen values (?,?,?)", t)
			conn.commit()
#	打印处理新刷卡UID后的记录列表
	c.execute('select * from xuesen')
	sjk=(c.fetchall())
#	print sjk
	n=len(sjk)
	print "现有记录数:",n
	i=0
	c.execute('select * from xuesen')
	while i<n:
		print i,")",(c.fetchone())
		i+=1
# 查询指定字段内容
#	c.execute("select * from xuesen where uid like '5166dc75'")
#	print c.fetchone()
# 修改指定记录某字段内容，并且显示出来
#	xh='2017090002'
#	xm='张小泉'
#	id='5166dc75'
#	c.execute("update xuesen set xuehao ='"+xh+"'  where uid='"+id+"'")		# 指定uid修改学号
#	c.execute("update xuesen set name ='"+xm+"'  where uid='"+id+"'")		# 指定uid修改姓名
#	conn.commit() 
#	c.execute("select * from xuesen where uid like '"+id+"'")
#	js=c.fetchone()
#	print js					# 这种方法显示内容是汉字的字段会出现16进制数值
#	print js[0],js[1],js[2]		# 这种方法正常显示内容是汉字的字段

# 取得CPU温度
	file1 = open("/sys/class/thermal/thermal_zone0/temp")
	temp = int(float(file1.read()) / 1000)
	file1.close()
	print "CPU温度："+str(temp)+" C    "
# 取得机箱环境温湿度
#	wsda=wsd()
#	wd="机箱温度:"+wsda[0]+"C  "
#	sd="湿度:"+wsda[1]+"%"
#	print wd,sd
	print "============================"
#	draw_rotated_text(disp.buffer,("温度:CPU="+str(temp)+"机箱="+wsda[0]+"湿度:"+wsda[1]+"%"), (24, 0), jd, font, fill=(125,g,125)) #显示机箱温度
#	disp.display()
	nx+=1
