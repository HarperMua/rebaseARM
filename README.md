# rebaseARM
rebase firmware under ARM processor based on [@mncoppola's basefind.py](https://github.com/mncoppola/ws30/blob/master/basefind.py) and [ARM设备固件装载基址定位的研究](http://cdmd.cnki.com.cn/Article/CDMD-10007-1018812112.htm)

## 原理
固件文件一般都包含一些字符串（strings）。固件中的字符串存放在内存中，一般通过字符串地址进行访问和操作。字符串地址一般通过LDR指令加载到寄存器中。因此，一个字符串的加载地址一定和一个字符串的内存地址。

字符串识别：遍历整个文件，将字符串的起始地址存放在集合s={s_1,s_2,s_3…s_n}中。字符串的识别通过正则表达式模式匹配进行。如下所示，我们定义字符串的字符集为ASCII编码格式的可打印字符，长度大于10。
 ```
chars = r"A-Za-z0-9/\-:.,_$%'\"()[\]<> "
min_length = 10
regexp = "[%s]{%d,}" % (chars, min_length

```
ARM状态下字符串加载地址识别：ARM固件一般通过LDR指令或者ADR指令将字符串的地址加载到寄存器中，但是ADR指令为基于PC的相对寻址方式，和固件的装载基址没有关系。因此，只考虑LDR指令加载的字符串地址。ARM状态下LDR指令的机器码格式如下所示，可以发现LDR指令开头部分为0x9FE5。

<img width="415" alt="image" src="https://user-images.githubusercontent.com/76193596/207274691-2837ec8b-a0c4-4ee0-964b-73e09ab3843d.png">

LDR指令的寻址地址计算如下：

address=(PC&0xFFFFFFFC)+imml2

Thumb状态下字符串加载地址识别：THUMB状态下LDR指令的机器码格式如下所示，可以发现LDR指令开头部分为b’01001。

<img width="292" alt="image" src="https://user-images.githubusercontent.com/76193596/207275976-cd59b92c-2cf7-4096-9eb1-3cff76bf87a8.png">

LDR指令的寻址地址计算如下：

address=(PC&0xFFFFFFFC)+imml8*4

因为ARM处理器采用3级流水线，对于ARM状态下的指令PC的取值为current+4，对于Thumb状态下的指令PC的取值为current+8。遍历固件，定位每一条LDR指令，计算出取值地址。根据取值地址，到内存中读取字符串的加载地址，记录在集合p={p_1,p_2,p_3…p_n}中。

字符串地址匹配获取基地址：如果某一个字符串在文件中的偏移量为s_i，加载到内存中位置为p_i，假设装载基址为base，则p_i=base+s_i。首先确定二进制文件装载基址的范围，其最小值为0x1000，因为固件地址一般都是0x1000对齐的，在32位嵌入式系统中装载基址的最大值为0xFFFFFFFF-fileSize，其中fileSize为二进制文件的大小。用集合p中每个元素p_i依次减去集合s中每个元素s_k，如果差值在装载基址的范围内则保存，否则舍弃。然后统计每个差值出现的次数，按出现次数进行降序排序并将结果输出。出现次数最多的元素即为候选装载基址。候选装载基址的实际意义为在这个内存地址处，集合s与集合p中有最多的元素存在着对应关系。

举例说明，如图所示，地址为0x38400000出现的次数远远大于其他地址。因此固件的基地址为0x38400000。

<img width="209" alt="image" src="https://user-images.githubusercontent.com/76193596/207276042-f48929db-f697-4caa-8693-17bdb9a0ac63.png">

## 使用
--min_addr和--max_addr定位基地址的范围，合理的缩小两者差可以有效提升运行速度。

--page_size用于保持基地址位对其，通常情况下与0x1000对齐

通过np.save和np.load存储运行的中间结果。对于比较大的固件，可以从某一个中间结果开始继续运行。

