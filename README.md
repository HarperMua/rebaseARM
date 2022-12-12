# rebaseARM
rebase firmware under ARM processor based on [@mncoppola's basefind.py](https://github.com/mncoppola/ws30/blob/master/basefind.py) and [ARM设备固件装载基址定位的研究](http://cdmd.cnki.com.cn/Article/CDMD-10007-1018812112.htm)

## 原理
固件文件一般都包含一些字符串（strings）。固件中的字符串存放在内存中，一般通过字符串地址进行访问和操作。字符串地址一般通过LDR指令加载到寄存器中。基地址base和字符串的加载地址p和字符串的内存地址s的关系如下：p=base+s

对于比较大的文件，运行时间较长，通过np.save和np.load存储中间的运行结果
