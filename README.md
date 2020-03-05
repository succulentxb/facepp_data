## Face++ 人脸稠密点数据自动收集

### 环境配置(Linux/Mac环境配置)
#### virtualenv 配置版本
- 在电脑安装`Python`环境，要求`python3` 
- 安装虚拟环境，`pip install virtualenv`
- 安装虚拟环境后，在该项目目录下创建虚拟环境`virtualenv -p python3 --no-site-packages venv`
- 激活虚拟环境`source ./venv/bin/activate`
- 安装依赖包`pip install -r requirements.txt`

#### anaconda 配置版本
- 电脑安装好`Anaconda3`
- 创建`conda`环境，在项目目录下`conda env create -f conda-env.yaml`
- 激活`conda`环境，`conda activate facepp`

### 获取图片人脸识别信息
- 本功能代码实现在`face_data.py`，具体的配置说明写在`face_data.py`的注释中，其中
- 配置好后，运行`python face_data.py`

### 处理人脸图片，加点
- 本功能代码实现在`img_process.py`中，具体的配置说明在`img_process.py`中
- 配置好后，运行`python img_process.py`

### 下载远程图片
- 功能代码实现在`img_download.py`中，运行`python img_download.py`