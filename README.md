# security-scripts

网络安全检测相关的 Python 脚本集合

## 脚本说明

### check_weak_pass.py

批量 URL 弱口令探测脚本

**功能：**
- 读取 urls.txt 中的目标地址
- 尝试常见弱口令组合（admin/admin, admin/password）
- 支持 DVWA 等靶场的 token 自动提取
- 根据响应内容判断登录是否成功

**使用方法：**
```bash
pip install requests
python check_weak_pass.py
