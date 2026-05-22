---
name: xufeng-material-navigator
description: |
  用于黄石旭丰新材料科技有限公司（模具钢、高速钢等特钢产品）的产品查询与官网自动导航。
  当用户询问公司是否有某产品、某牌号的详细信息，或希望了解公司更多信息时，调用 agent_browser 工具帮助用户导航到公司官网的对应页面。
---

# xufeng-material-navigator Skill 
## 触发条件
在以下情况下，你应该主动调用此技能：
- 用户询问某个具体牌号（如"H13"）是否有详细信息
- 用户询问某个产品品类（如"你们公司的冷作模具钢有哪些"
- 用户询问公司简介、联系方式、产能等信息
- 用户询问"牌号对照表"或"规格表"
- 用户询问与公司产品相关的其他信息


## 执行流程

### 第 1 步：分析对话内容弄清需求
- 判断用户的具体需求：是询问某个牌号、某个品类，还是公司信息
- 根据需求确定要导航的页面路径和要展示的简短内容

### 第 2 步：工具调用

使用以下参数调用 `agent_browser` 工具：

### 第 3 步：返回工具调用结果
- 只返回工具调用的结果，不要额外添加任何自然语言解释或寒暄
- 确保返回的JSON格式正确，包含正确的URL和简短内容

## 核心原则 - 工具调用

- 用户有明确的牌号或产品品类需求时，**先给出简短的自然语言介绍，然后立即调用 agent_browser 工具**。
- 用户只询问公司简介（如"你们公司做什么的"），调用 `agent_browser`，url 为 `/`，content 简述公司定位。
- 用户询问"牌号对照表"或"规格表"，调用 `agent_browser`，url 分别为 `/products/comparison/` 或 `/products/specs/`。
- 用户询问联系方式，调用 `agent_browser`，url 为 `/contact/`。

## 工具调用方法

使用以下参数调用 `agent_browser` 工具：

- `url`: 相对路径（如 `/products/cold-work/d2/`），工具会自动补全为 `https://www.xufengmaterial.com.cn` + 路径
- `content`: 一行简短介绍，包含产品的硬度、典型应用等信息

调用示例：
```
agent_browser(url="/products/high-speed/m42/", content="M42 含钴高速钢，硬度 HRC66-70，适合高性能切削刀具。")
```



## 产品体系与页面导航

### 产品大类首页

| 品类 | 页面路径 |
|------|----------|
| Cold Work Die Steel（冷作模具钢） | `/products/cold-work/` |
| Hot Work Die Steel（热作模具钢） | `/products/hot-work/` |
| Plastic Mold Steel（塑料模具钢） | `/products/plastic-mold/` |
| High Speed Steel（高速工具钢） | `/products/high-speed/` |

### 冷作模具钢（12款）

主页：`/products/cold-work/`

| 牌号 | 页面路径 | 硬度 | 典型应用 |
|------|----------|------|----------|
| Cr12MoV | `/products/cold-work/cr12mov/` | 退火≤255HB，HRC58-62 | 冲裁模、冷镦模 |
| Cr12 | `/products/cold-work/cr12/` | 退火≤269HB，HRC60-64 | 冷挤压模、剪切片 |
| SKD11 | `/products/cold-work/skd11/` | 退火≤255HB，HRC58-62 | 冲裁模、量规 |
| D2 | `/products/cold-work/d2/` | 退火≤255HB，HRC58-62 | 冷作模具、滚丝模 |
| DC53 | `/products/cold-work/dc53/` | 退火≤255HB，HRC60-63 | 高韧性冷作模具 |
| 1.2379 | `/products/cold-work/12379/` | 退火≤255HB，HRC58-62 | 耐磨冲压模具 |
| 1.2436 | `/products/cold-work/12436/` | 退火≤255HB，HRC60-64 | 高耐磨冷作模具 |
| 1.2510 | `/products/cold-work/12510/` | 退火≤230HB，HRC58-62 | 油淬冷作钢 |
| 1.2601 | `/products/cold-work/12601/` | 退火≤255HB，HRC60-64 | 高碳高铬冷作钢 |
| 9CrWMn | `/products/cold-work/9crwmn/` | 退火≤241HB，HRC56-62 | 耐冲击冷作模具 |
| Cr8Mo2SiV | `/products/cold-work/cr8mo2siv/` | 退火≤255HB，HRC60-63 | 替代Cr12型钢 |
| Cr12Mo1V1 | `/products/cold-work/cr12mo1v1/` | 退火≤255HB，HRC59-62 | 耐磨冷作模具 |

### 热作模具钢（12款）

主页：`/products/hot-work/`

| 牌号 | 页面路径 | 硬度 | 典型应用 |
|------|----------|------|----------|
| H13 | `/products/hot-work/h13/` | 退火≤229HB，HRC44-52 | 压铸模、热挤压模 |
| 1.2344 | `/products/hot-work/12344/` | 退火≤229HB，HRC44-52 | 同H13 |
| SKD61 | `/products/hot-work/skd61/` | 退火≤229HB，HRC44-52 | 同H13 |
| 4Cr5MoSiV | `/products/hot-work/4cr5mosiv/` | 退火≤229HB，HRC40-48 | 热锻模 |
| H11 | `/products/hot-work/h11/` | 退火≤229HB，HRC40-47 | 热剪切刀片 |
| 1.2343 | `/products/hot-work/12343/` | 退火≤229HB，HRC42-50 | 高韧性热作钢 |
| 8407 | `/products/hot-work/8407/` | 退火≤215HB，HRC45-52 | 高级压铸模 |
| 8418 | `/products/hot-work/8418/` | 退火≤215HB，HRC46-52 | 高寿命热锻模 |
| 1.2367 | `/products/hot-work/12367/` | 退火≤229HB，HRC44-52 | 高热疲劳韧性 |
| 5CrNiMo | `/products/hot-work/5crnimo/` | 退火197-241HB，HRC38-47 | 大型热锻模 |
| 1.2714 | `/products/hot-work/12714/` | 退火≤248HB，HRC38-48 | 韧性热作钢 |
| 3Cr2W8V | `/products/hot-work/3cr2w8v/` | 退火≤255HB，HRC44-52 | 高温强度好 |

### 塑料模具钢（4款）

主页：`/products/plastic-mold/`

| 牌号 | 页面路径 | 硬度 |
|------|----------|------|
| 718H | `/products/plastic-mold/718h/` | 预硬HRC33-38 |
| P20 | `/products/plastic-mold/p20/` | 预硬HRC28-32 |
| S136 | `/products/plastic-mold/s136/` | 退火≤215HB，HRC48-54 |
| NAK80 | `/products/plastic-mold/nak80/` | 预硬HRC37-43 |

### 高速工具钢（4款）

主页：`/products/high-speed/`

| 牌号 | 页面路径 | 硬度 |
|------|----------|------|
| M2 | `/products/high-speed/m2/` | 退火≤248HB，HRC63-66 |
| M35 | `/products/high-speed/m35/` | 退火≤269HB，HRC64-67 |
| M42 | `/products/high-speed/m42/` | 退火≤269HB，HRC66-70 |
| M51 | `/products/high-speed/m51/` | 退火≤269HB，HRC64-67 |

### 其他常用页面

| 页面 | 路径 |
|------|------|
| 首页 | `/` |
| 关于我们 | `/about/` |
| 产品中心 | `/products/` |
| 牌号对照表 | `/products/comparison/` |
| 产品规格表 | `/products/specs/` |
| 联系我们 | `/contact/` |

## 牌号匹配规则

匹配时**大小写不敏感**。用户输入中包含以下关键词即匹配对应品类：

- **冷作模具钢：** D2, SKD11, Cr12MoV, DC53, 1.2379, 1.2436, 1.2510, 1.2601, 9CrWMn, Cr8Mo2SiV, Cr12Mo1V1, Cr12
- **热作模具钢：** H13, 1.2344, SKD61, 4Cr5MoSiV, H11, 1.2343, 8407, 8418, 1.2367, 5CrNiMo, 1.2714, 3Cr2W8V
- **塑料模具钢：** 718H, P20, S136, NAK80
- **高速工具钢：** M2, M35, M42, M51
