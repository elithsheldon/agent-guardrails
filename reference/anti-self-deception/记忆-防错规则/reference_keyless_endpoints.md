---
name: keyless-endpoints
description: 免 key 检索/抓取端点修法台账（HN Algolia / Reddit 三件套 / Jina Reader / 东大 IP 搜索实测）——07-31 全部本机 live 验证；此类第三方端点行为衰减快，用前先小探一发
metadata: 
  node_type: memory
  type: reference
  originSessionId: b9615971-4254-47d7-9e06-aeb196e7af44
  modified: 2026-07-31T01:52:12.465Z
---

2026-07-31 从 mvanhorn/last30days-skill 代码深潜收割（判定台账=[[x-tool-scouting]]，端点原始代码引用见 ~/kb_tools/scout_reports/2026-07-31_code_dive/last30days-skill.json）。全部条目当日从本服务器（东大学术网出口 IP）实测可用。**衰减警告：本次就发现上游一条 lore 已过期（HN points 过滤）、一条方向反转（DDG/Startpage）——这类笔记用前先单发小探，别直接批量。**

## HN Algolia（结构化检索；WebSearch 做不到日期+分数过滤）
- 端点：`hn.algolia.com/api/v1/search`（相关性排序）/ `…/search_by_date`（时间序）/ `…/items/<id>`（单帖含全评论树）
- 时间窗：`numericFilters=created_at_i><unix秒>`
- ⚠️ 多词查询必须加 `optionalWords=<原查询串>`，否则默认 AND 直接全灭（07-31 实测：4 词查询无它 0 hits、加它 1426 hits）——scoop 类检索的致命开关
- 分数过滤：`numericFilters=points>10` 现已服务端生效（07-31 实测 nbHits 随阈值收紧）；上游代码注释「points 过滤必 400、只能超采后客户端滤」已失效——衰减实例
- 定位：RL/agent/工具类话题社区讨论密度最高的免 key 源

## Reddit 免 key 三件套（`.json` 端点对无 key 请求=403）
- 发现：`reddit.com/r/<sub>/search.rss?q=<查询>&restrict_sr=1`（RSS 仍 200）
- 评论：`reddit.com/svc/shreddit/comments/r/<sub>/t3_<id>?sort=top` → HTML partial，`<shreddit-comment score=…>` 属性即真实分数，sort=top 保证首屏高票
- 分数批量回填：`arctic-shift.photon-reddit.com/api/posts/ids?ids=t3_…,t3_…`（≤50 id/请求；422=降速信号；07-31 实测 200 含完整帖对象）
- ⚠️ shreddit 端点属反爬军备竞赛，是「当前修法」不是长期依赖

## Jina Reader（JS 渲染页兜底）
- `r.jina.ai/<完整URL>` → 服务端渲染后出干净 markdown（07-31 实测 arXiv abs 页 200）
- 与 WebFetch 分工：WebFetch 不渲染 JS；撞上 JS 页且无 API 修法时先用它（一行成本，优先于装 Crawl4AI——见 [[x-tool-scouting]] watchlist 唤醒条件）
- ⚠️ 三条代价（上游源码自记）：免费层限速 / 可能吐缓存旧快照 / **URL 泄露给第三方——凡带 token/私有路径的 URL 禁用**

## 本机搜索兜底实测（东大学术 IP ≠ 云数据中心 IP）
- `html.duckduckgo.com/html/?q=…` → 200 有 10 条有机结果；Startpage → 303 captcha（挑战页参数明认出 The University of Tokyo）
- 与外部 lore 恰好相反（数据中心 IP 上 DDG 拦、Startpage 通）——排障以本机实测为准，别照抄外部经验

## ⚠️ 「有开放获取」不等于拿得到，更不等于拿到的是同一篇（2026-08-15 实测，另一会话发现、本会话复现）

判一篇论文能不能取到时，**聚合站说 is_oa=true 只是一个指针，不是文件本身**，而指针可能指错。

**当天判例**：Bloem 等《Synthesizing Robust Systems》期刊版（Acta Informatica 2014，
DOI `10.1007/s00236-013-0191-5`，**8 位作者**）。Unpaywall 报 `is_oa: true`，
唯一的开放位置是某机构仓库的一条记录、标着 `submittedVersion`。实际去取：
- 该仓库的 PDF 直链**返回的是 HTML 网页不是 PDF**（本会话复现）；
- 而网上所有号称该 DOI 有开放获取的指针**最终都汇向同一个文件**，另一会话下载后逐字核过，
  **那是 2009 年的会议版**（`10.1109/fmcad.2009.5351139`，**4 位作者**、8 页，
  PDF 元数据是 `FMCAD.dvi`、日期 2009-10-02），被机构仓库错标成了期刊版的投稿版。

**两版差异是实质性的**：会议版只做 safety、无实验，结论节明写 liveness 是 open question；
期刊版是 safety + liveness + GR(1) + 实验，新增的 4 位作者正是后续两篇论文的作者。
**照聚合站的「OA available」去拿，会拿到另一篇论文而不自知。**

**纪律**：
1. **作者数、页数、年份三项对不上就是另一篇**——取到后先核这三项，再核 PDF 元数据里的
   生成文件名与日期（`FMCAD.dvi` 这种一眼就露馅）。
2. 判「取不到」之前把能试的都试过并写清试了哪些（当天试过 Semantic Scholar / Unpaywall /
   OpenAlex / scholar.archive.org / DBLP / arXiv / 两个机构仓库 / 六位作者主页 / 出版方直连）；
   ⛔ 只写「找不到」而不写试过什么，下一个人会从头再试一遍。
3. 用 Crossref 按标题查能一次看清同名不同版：
   `api.crossref.org/works?query.bibliographic=<标题+作者+刊名>&rows=3`，
   返回里的作者数与刊名直接把会议版和期刊版分开。


## ⛔⛔ 2026-08-23 新增一个衰减实例，而且是新形态：**整个接口被人机验证挡住**

本页开头那条「衰减警告」举的两个实例都是**行为变了**（一条过滤失效、一条方向反转）。⭐ **这一次是另一种：接口还在，但它现在要求先通过人机验证。**

某个会议评审平台的元数据接口，本机实测（新旧两个域名都试了）：

```
curl -s -w "HTTP %{http_code}" "https://api2.openreview.net/notes?forum=<编号>"
→ HTTP 403
{"name":"ChallengeRequiredError",
 "message":"Challenge verification required (2026-08-23-1126812)",
 "status":403,
 "details":{"challengeUrl":"https://openreview.net/challenge?redirect=…"}}
```

⭐⭐ **这个形态必须和限流分开，否则会白耗时间**：

| 返回 | 意思 | 该怎么做 |
|---|---|---|
| 429 或超时 | 限流或网络抖动 | ⭐ 退避后重试，多半会通 |
| ⛔ **403 加上「需要通过人机验证」** | ⛔ **这条路对脚本关闭了** | ⛔ **重试多少次都没用**，改走别的来源或上报 |

⚠️ **两者都是「取不到」，而重试对后者完全无效。** ⛔ **看返回体，不要只看状态码。**

**连带后果**：库里另一条记忆（讲那个平台可达性的那条）写着「元数据接口是通的，只有文件字节取不到」——⛔ **那句已不成立**，已在那条上标注过期。⭐ 凡是只能靠那个平台的编号定位的条目，**现在从本机核不了著录**；⚠️ **处置是写成「当前核不到」，不是「不存在」**——这两个是不同的结论。

## ⛔⛔ 2026-08-23 第三种形态：**接口是活的，而你的请求根本没到它那里**

前两条讲的是「接口变了」和「接口关了」。⭐ **这一条讲的是接口好好的，返回却是空的**——而空返回和「查无此物」在下游代码里长得一模一样。

**实测**：查一篇论文有没有 arXiv 版，连查四次全部零命中，其中包括一次**故意选的对照查询**（查一位已知发过几十篇预印本的作者），也是零。看上去像铁证。

```
curl -s  "http://export.arxiv.org/api/query?search_query=all:electron"   → 0 字节
curl -s -o f -w '%{http_code}' "http://export.arxiv.org/..."             → 301，响应体 0 字节
curl -sL "https://export.arxiv.org/api/query?search_query=all:electron"  → 4457 字节，2 条
```

⛔ **`http://export.arxiv.org` 现在 301 跳到 https，而 `curl` 不带 `-L` 不跟跳转**，于是拿到一个**成功退出、零字节**的响应。⚠️ **`curl -s` 什么都不打印，退出码是 0**，解析器在空文本上找不到 `<entry>`，老老实实报「0 条」。**每一环都工作正常，合起来是一句假话。**

⭐⭐ **真正该记的不是这个域名，是那个对照查询为什么没救得了我**：

> **对照查询只有在它和正式查询走不同的管子时才算对照。** ⛔ 我那次对照和正式查询用的是同一条 `curl`、同一个协议、同一个解析函数——**管子坏了，两边一起坏**，于是对照返回零反而让我更确信「库里就是没有」。

**做法**（这三条一起才成立，少一条就漏）：
- ⭐ 凡是要用「零命中」下结论的请求，**一律 `-L` 跟跳转**，并且 **`-w '%{http_code} %{size_download}'` 把状态码和字节数打出来**。
- ⛔ **字节数为 0 = 本次查询没有结论**，不许当成「没有」。⚠️ 这和 `200` 与否无关，301/302 也会给 0 字节。
- ⭐ 对照查询要选**已知一定有结果**的，并且**先看它的字节数**：对照也返回 0 字节，说明坏的是管子，此时**正式查询的零命中作废**，不是「双重确认」。

**同源判例**：本页上一节那个平台的 403 是「路关了」，这一条是「路通着但我没走上去」。⭐ **两者的共同点是返回体里有答案而状态码里没有**——⛔ 别只看状态码，也别只看命中数，**先看字节数**。
