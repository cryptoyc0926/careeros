"""
简历变体测试数据集 - 同一人物（张展）的5个不同职业方向版本
"""

RESUME_VARIANTS = {
    "backend": """meta:
  name: 张展
  phone: 13800138000
  email: zhangzhan@example.com
  location: 北京
  current_title: 高级后端工程师
  years_of_experience: 6

summary_variants:
  - 6年互联网后端开发经验，擅长分布式系统和微服务架构。精通Go/Python，
    有高并发系统优化经验，参与过日均流量10亿+的推荐系统开发。
  - 技术深度：掌握消息队列（Kafka/RabbitMQ）、缓存（Redis）、数据库等核心组件设计。
    曾主导系统重构，性能提升50%，代码质量评分提升30%。

experience:
  - company: 字节跳动
    department: 推荐算法部
    position: 高级后端工程师
    duration: "2021年1月 - 至今"
    achievements:
      - content: "设计并实现推荐系统服务治理框架，支撑日均50亿请求，可用性99.99%"
        tags: [分布式系统, 服务治理, 高可用]
        metrics: "日均50亿请求, 99.99%可用性"
      - content: "重构用户画像服务，采用Redis+Kafka架构，实时性提升10倍，成本降低40%"
        tags: [系统优化, 缓存, 消息队列]
        metrics: "实时性提升10倍, 成本降低40%"
      - content: "主导Go服务框架升级，支持自适应超时和限流，接入50+微服务"
        tags: [微服务架构, RPC框架, Go]
        metrics: "接入50+微服务, 故障率降低60%"
      - content: "建设代码质量平台，集成静态分析、测试覆盖率检测，显著提升团队代码水平"
        tags: [工程效能, 质量管理]
        metrics: "代码覆盖率从65%->85%, 缺陷率降低50%"

  - company: 阿里巴巴
    department: 淘宝技术部
    position: 后端工程师
    duration: "2018年6月 - 2020年12月"
    achievements:
      - content: "参与商品服务核心链路优化，设计分层缓存方案，P99延迟从200ms降至50ms"
        tags: [缓存策略, 性能优化, Java]
        metrics: "P99延迟200ms->50ms, QPS提升3倍"
      - content: "建立商品搜索倒排索引实时更新机制，支撑日均10亿+搜索请求"
        tags: [搜索引擎, Elasticsearch, 实时计算]
        metrics: "日均10亿+请求, 更新延迟<100ms"
      - content: "设计并实现数据一致性监控平台，发现并修复30+线上数据不一致问题"
        tags: [数据一致性, 监控告警, 故障排查]
        metrics: "覆盖50+核心表, 日均检测1000+异常"

  - company: 京东
    department: 基础架构部
    position: 初级后端工程师
    duration: "2017年7月 - 2018年5月"
    achievements:
      - content: "参与订单服务重构，使用Spring Cloud框架改造单体应用，支持秒级扩容"
        tags: [微服务, Spring Cloud, Java]
        metrics: "服务响应时间降低30%, 支持自动扩容"
      - content: "实现库存同步服务，保证多个仓库库存一致性，故障恢复时间<5分钟"
        tags: [分布式事务, 数据同步]
        metrics: "同步延迟<1s, 可用性99.5%"

skills:
  - category: 编程语言
    items: [Go(精通), Python(精通), Java(熟练), SQL(精通)]
  - category: 分布式系统
    items: [Kafka, RabbitMQ, Redis, Elasticsearch, 一致性算法]
  - category: 框架和工具
    items: [Gin, Spring Boot, MySQL, MongoDB, Docker, Kubernetes]
  - category: 其他
    items: [高并发设计, 性能优化, 系统监控, 故障排查]

education:
  - school: 北京理工大学
    degree: 计算机科学与技术 (本科)
    year: 2017
""",

    "product_manager": """meta:
  name: 张展
  phone: 13800138000
  email: zhangzhan@example.com
  location: 北京
  current_title: 产品经理
  years_of_experience: 5

summary_variants:
  - 5年互联网产品经验，擅长用户增长和数据驱动决策。曾主导多个千万级DAU产品的
    功能设计和上线，对社交、内容、工具类产品有深入理解。
  - 专长：用户增长黑客、A/B测试、数据分析、竞品分析。带领团队实现用户增长50%+，
    商业化收入增长3倍。

experience:
  - company: 字节跳动
    department: 社交产品部
    position: 高级产品经理
    duration: "2021年3月 - 至今"
    achievements:
      - content: "主导短视频推荐算法产品化，设计用户个性化feeding体验，用户停留时长增长30%"
        tags: [推荐算法, 产品设计, 用户增长]
        metrics: "用户停留时长+30%, 日活增长2000万"
      - content: "规划社交互动功能矩阵，推出私信、评论、分享等核心功能，驱动用户活跃度提升"
        tags: [社交功能, 用户活跃, 功能设计]
        metrics: "互动率提升45%, 人均互动次数+50%"
      - content: "建立用户增长指标体系和增长漏斗分析框架，识别瓶颈并执行优化，新用户留存率从30%->45%"
        tags: [增长分析, 数据驱动, 指标体系]
        metrics: "新用户7日留存30%->45%, 14日留存提升35%"
      - content: "与研发团队协作A/B测试平台建设，支持快速实验迭代，月均发起50+实验"
        tags: [A/B测试, 实验设计, 数据分析]
        metrics: "实验周期从2周->3天, 取样精度提升到95%"

  - company: 腾讯
    department: 产品中心
    position: 产品经理
    duration: "2018年9月 - 2021年2月"
    achievements:
      - content: "主导内容平台运营功能升级，创新话题、标签、推荐系统，用户发布量增长120%"
        tags: [内容生态, 功能创新, 用户激励]
        metrics: "日发布内容+120%, 用户参与率+60%"
      - content: "制定用户激励政策，推出等级、勋章、积分系统，驱动高价值用户留存增长50%"
        tags: [用户激励, 游戏化设计, 留存优化]
        metrics: "高价值用户留存+50%, 月均活跃+35%"
      - content: "进行竞品分析和市场调研，发现短视频内容红利，提出并推进短视频功能立项"
        tags: [竞品分析, 市场研究, 战略规划]
        metrics: "短视频功能上线3月达DAU500万"
      - content: "与数据分析团队合作，建立产品健康度仪表板，覆盖30+核心指标，支撑决策"
        tags: [数据分析, BI仪表板, 决策支持]
        metrics: "覆盖30+指标, 周报阅读量500+人次"

  - company: 美团
    department: 平台事业部
    position: 初级产品经理
    duration: "2017年8月 - 2018年8月"
    achievements:
      - content: "负责商家侧功能设计，推出订单管理、库存同步等功能，商家效率提升40%"
        tags: [B2B产品, 功能设计, 商家赋能]
        metrics: "商家日均管理时间降低40%, 满意度评分4.5/5"
      - content: "执行用户调研访谈20+次，收集商家反馈，指导产品优化方向"
        tags: [用户研究, 产品规划]
        metrics: "20+深度访谈, 发现3个重点需求方向"

skills:
  - category: 产品能力
    items: [用户增长, 数据驱动, A/B测试, 竞品分析, 用户研究]
  - category: 工具
    items: [SQL数据查询, Google Analytics, Power BI, Figma原型, 用户调研工具]
  - category: 业务理解
    items: [社交产品, 内容生态, 变现模式, 用户心理学, 增长黑客]

education:
  - school: 北京理工大学
    degree: 计算机科学与技术 (本科)
    year: 2017
""",

    "data_analyst": """meta:
  name: 张展
  phone: 13800138000
  email: zhangzhan@example.com
  location: 北京
  current_title: 高级数据分析师
  years_of_experience: 5

summary_variants:
  - 5年互联网数据分析经验，精通SQL和Python数据分析。建立过多套核心业务指标体系和
    自动化分析系统，用数据驱动产品和运营决策。
  - 专长：大规模数据挖掘、因果推断、AB测试分析、SQL优化。曾通过数据分析识别
    产品瓶颈，推动功能优化，为公司创造2000万+收入增长。

experience:
  - company: 字节跳动
    department: 数据分析团队
    position: 高级数据分析师
    duration: "2021年2月 - 至今"
    achievements:
      - content: "建立推荐系统核心指标体系（CTR、转化、留存等），日均输出30+报表，支撑400+决策"
        tags: [指标体系, SQL, 数据仓库]
        metrics: "覆盖100+指标, 日均报表查询500+次"
      - content: "设计推荐算法AB测试框架，进行100+次实验，精准评估新特性效果，提升点击率15%"
        tags: [AB测试, 因果推断, 实验设计]
        metrics: "点击率提升15%, CTR增长3000万"
      - content: "进行用户行为深度分析，识别高价值用户特征，指导运营精细化策略，转化率提升25%"
        tags: [用户分析, 行为分析, 分割策略]
        metrics: "转化率+25%, 人均收入+30%"
      - content: "使用Python进行机器学习模型构建（预测用户流失、推荐倾向），模型准确度达88%"
        tags: [机器学习, Python, 预测模型]
        metrics: "留存预测准确度88%, 流失预警覆盖80%用户"

  - company: 阿里巴巴
    department: 数据分析部
    position: 数据分析师
    duration: "2018年7月 - 2021年1月"
    achievements:
      - content: "建立商品销量预测模型，准确度达92%，支撑库存优化和营销计划，库存成本降低20%"
        tags: [时间序列预测, 机器学习, 库存优化]
        metrics: "预测准确度92%, 库存成本-20%, 缺货率-15%"
      - content: "分析商家行为数据，发现价格敏感度、转化漏斗等规律，提出精细化定价建议，GMV增长5%"
        tags: [商业分析, 消费者行为, 定价策略]
        metrics: "GMV增长5%, 直接收入增长8000万"
      - content: "搭建自动化分析系统，日均处理数据100TB+，支撑实时决策，分析效率提升60%"
        tags: [数据仓库, ETL, 自动化, Python]
        metrics: "日处理数据100TB+, 查询响应时间<5s"
      - content: "使用SQL和Python进行竞品分析，生成周度竞争力报告，支撑战略制定"
        tags: [竞品分析, SQL, 数据可视化]
        metrics: "覆盖50+竞品, 周度分析报告5份"

  - company: 京东
    department: 商业分析部
    position: 初级数据分析师
    duration: "2017年9月 - 2018年6月"
    achievements:
      - content: "编写SQL查询脚本分析订单数据，识别高价值客户，指导精准营销，转化率提升18%"
        tags: [SQL, 客户分析, 精准营销]
        metrics: "转化率+18%, ROI提升25%"
      - content: "建立销售漏斗分析模型，识别转化瓶颈，优化流程后订单完成率从75%->82%"
        tags: [漏斗分析, 流程优化]
        metrics: "订单完成率75%->82%, 日均订单+12%"

skills:
  - category: 数据技能
    items: [SQL(精通), Python(精通), Tableau, Power BI, 数据仓库]
  - category: 分析方法
    items: [AB测试, 因果推断, 漏斗分析, 用户分割, 时间序列分析]
  - category: 机器学习
    items: [预测模型, 分类算法, 特征工程, TensorFlow]
  - category: 其他
    items: [统计学基础, 数据可视化, 商业分析, 战略规划]

education:
  - school: 北京理工大学
    degree: 计算机科学与技术 (本科)
    year: 2017
""",

    "ai_researcher": """meta:
  name: 张展
  phone: 13800138000
  email: zhangzhan@example.com
  location: 北京
  current_title: AI研究员
  years_of_experience: 4

summary_variants:
  - 4年AI算法研究经验，专注深度学习和计算机视觉。发表10+篇顶级会议论文
    （CVPR/ICCV/NeurIPS），参与过多个产业化项目，算法创新能力强。
  - 研究方向：目标检测、语义分割、多模态学习。掌握PyTorch/TensorFlow框架，
    有大规模模型训练和推理优化经验。

experience:
  - company: 商汤科技
    department: 视觉研究院
    position: 高级研究员
    duration: "2021年4月 - 至今"
    achievements:
      - content: "提出高效目标检测算法HRDet，精度提升8%，推理速度提升3倍，论文被CVPR 2023录用"
        tags: [目标检测, 深度学习, 论文发表]
        metrics: "论文CVPR 2023录用, 引用次数50+, 开源star 2000+"
      - content: "研发多模态融合框架，融合视觉和文本信息进行跨模态检索，准确度达95.6%"
        tags: [多模态学习, 跨域融合, NLP]
        metrics: "准确度95.6%, 已应用到3个商业产品"
      - content: "优化推理框架，支持模型量化和蒸馏，推理速度提升5倍，部署到1000+终端"
        tags: [模型优化, 量化, 边缘计算]
        metrics: "推理速度提升5倍, 模型大小降低80%, 部署1000+设备"
      - content: "指导5名实习生，合作发表3篇论文，建立高水平研究团队"
        tags: [团队管理, 人才培养, 学术指导]
        metrics: "3篇论文发表, 学生均获offer"

  - company: 蔚来汽车
    department: 自动驾驶部
    position: 算法工程师
    duration: "2019年1月 - 2021年3月"
    achievements:
      - content: "开发端到端多传感器融合感知系统，检测精度达98%，支持L4级自动驾驶功能"
        tags: [传感器融合, 多任务学习, 自动驾驶]
        metrics: "检测精度98%, 覆盖50+类物体, 已上车测试"
      - content: "提出轻量化语义分割网络，精度保持95%前提下推理延迟<100ms，可在车端部署"
        tags: [语义分割, 轻量化网络, 实时性]
        metrics: "延迟<100ms, 精度95%, 内存占用<100MB"
      - content: "收集和标注30万自动驾驶场景数据，构建行业内规模最大的标注数据集"
        tags: [数据集构建, 标注管理, 质量保证]
        metrics: "30万帧, 50+场景类型, 标注准确度99.5%"
      - content: "开发数据驱动的故障分析系统，识别模型失败案例，指导数据采集策略"
        tags: [失败分析, 数据策略, 持续改进]
        metrics: "分析覆盖5000+失败案例, 改进覆盖率从60%->92%"

  - company: 商汤科技
    department: 研究院
    position: 研究员
    duration: "2019年1月 - 2021年1月"
    achievements:
      - content: "提出adaptive attention机制，在ImageNet上提升精度1.5%，论文被ICCV 2020录用"
        tags: [注意力机制, CNN, 论文发表]
        metrics: "论文ICCV 2020录用, 引用50+次"
      - content: "研究知识蒸馏方法，将ResNet50压缩到ResNet18大小，精度保留98%"
        tags: [知识蒸馏, 模型压缩, 效率优化]
        metrics: "模型大小降低90%, 推理速度3倍, 精度保留98%"
      - content: "建立深度学习实验框架，集成50+种骨干网络，支持快速原型迭代"
        tags: [深度学习框架, PyTorch, 工程工具]
        metrics: "支持50+网络架构, 实验周期<1周"

skills:
  - category: 深度学习
    items: [CNN, Transformer, 多任务学习, 强化学习, 知识蒸馏]
  - category: 计算机视觉
    items: [目标检测, 语义分割, 实例分割, 多模态学习, 3D视觉]
  - category: 编程框架
    items: [PyTorch(精通), TensorFlow(精通), CUDA, 模型部署优化]
  - category: 其他
    items: [论文阅读与写作, 学术报告, 开源社区, 数据标注管理]

education:
  - school: 北京理工大学
    degree: 计算机科学与技术 (硕士)
    year: 2019
  - school: 北京理工大学
    degree: 计算机科学与技术 (本科)
    year: 2017
""",

    "fullstack": """meta:
  name: 张展
  phone: 13800138000
  email: zhangzhan@example.com
  location: 北京
  current_title: 全栈工程师
  years_of_experience: 5

summary_variants:
  - 5年全栈开发经验，精通前端（React/Vue）和后端（Node.js/Python/Go）。
    有完整的Web应用从设计、开发、测试到部署的经验。
  - 专长：React生态、Node.js框架、Docker/Kubernetes、性能优化。
    主导过多个产品从0到1的开发，用户规模达到百万级。

experience:
  - company: 字节跳动
    department: 基础平台部
    position: 高级全栈工程师
    duration: "2021年3月 - 至今"
    achievements:
      - content: "独立设计开发内部工具平台前后端，前端采用React+TypeScript，后端使用Node.js/Go，支撑5000+员工使用"
        tags: [React, TypeScript, Node.js, Go, 全栈]
        metrics: "日活5000+, 页面加载时间<2s, 后端API响应<100ms"
      - content: "优化前端性能，使用代码分割、懒加载、虚拟滚动等技术，首屏加载从3.5s->0.9s，提升290%"
        tags: [前端性能, 代码分割, React优化]
        metrics: "首屏加载3.5s->0.9s, Core Web Vitals全绿"
      - content: "设计微前端架构，支持50+个独立子应用并行开发，提升10个团队开发效率30%"
        tags: [微前端, 模块化, 架构设计]
        metrics: "50+子应用, 并发开发10个团队, 构建时间<30s"
      - content: "搭建容器化开发和部署流程，使用Docker和Kubernetes自动部署，从手工部署到全自动，故障率降低80%"
        tags: [Docker, Kubernetes, CI/CD, 部署自动化]
        metrics: "部署时间<5min, 故障率-80%, 可用性99.95%"

  - company: 美团
    department: 商家事业部
    position: 全栈工程师
    duration: "2018年8月 - 2021年2月"
    achievements:
      - content: "从0到1开发商家管理后台，前端使用Vue.js+Antd，后端使用Spring Boot，日均20万商家使用"
        tags: [Vue.js, Spring Boot, Java, Antd]
        metrics: "日活20万, 响应时间<150ms, 支持1000QPS"
      - content: "实现复杂的数据可视化报表系统，使用ECharts和D3.js绘制30+类图表，支持动态钻取分析"
        tags: [数据可视化, ECharts, D3.js, React]
        metrics: "支持30+图表类型, 渲染性能<500ms"
      - content: "优化后端API性能，设计缓存策略、数据库索引优化、查询优化，API响应时间从800ms->200ms"
        tags: [API优化, 缓存, 数据库优化, SQL]
        metrics: "API响应800ms->200ms, QPS提升4倍"
      - content: "建立测试框架，编写单元测试和集成测试，代码覆盖率80%，故障率下降50%"
        tags: [单元测试, 集成测试, Jest, Pytest]
        metrics: "覆盖率80%, 故障率-50%, 线上问题-40%"

  - company: 京东
    department: 商城平台部
    position: 初级全栈工程师
    duration: "2017年8月 - 2018年7月"
    achievements:
      - content: "开发商品详情页前端交互功能，使用原生JavaScript和jQuery，实现SKU选择、图片预览等复杂交互"
        tags: [JavaScript, jQuery, HTML/CSS, 交互设计]
        metrics: "页面加载<2s, 月均PV 1亿"
      - content: "参与后端服务开发，使用Spring框架开发商品服务API，支持秒级查询"
        tags: [Spring, Java, API开发, MySQL]
        metrics: "QPS 10000+, 响应时间<100ms"
      - content: "使用Docker容器化应用，配置容器编排，实现自动部署和扩容"
        tags: [Docker, 容器化, 部署自动化]
        metrics: "部署时间从1小时->15分钟"

skills:
  - category: 前端技术
    items: [React(精通), Vue.js(精通), TypeScript, HTML/CSS, Webpack]
  - category: 后端技术
    items: [Node.js(精通), Go(精通), Python(精通), Java(熟练), Spring Boot]
  - category: 数据库和工具
    items: [MySQL, MongoDB, Redis, Docker, Kubernetes, Git]
  - category: 其他
    items: [全栈架构设计, 微前端, 性能优化, CI/CD, 单元测试]

education:
  - school: 北京理工大学
    degree: 计算机科学与技术 (本科)
    year: 2017
"""
}
