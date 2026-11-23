<template>
  <div class="pm-app">
    <!-- ============ 左侧：集合 / 历史 / 环境 ============ -->
    <aside class="pm-side">
      <div class="side-head">
        <div class="side-title">API Workbench</div>
        <div class="side-actions">
          <button class="ico-btn" title="新建集合" @click="newCollection">＋集合</button>
          <button class="ico-btn" title="新建请求" @click="newRequest">＋请求</button>
        </div>
      </div>
      <div class="io-bar">
        <button class="io-btn" title="导入 Postman Collection v2.1 JSON" @click="triggerImport">⇩ 导入 Postman 集合</button>
        <button class="io-btn" title="导出为 Postman Collection v2.1 JSON" @click="showExport = true">⇧ 导出</button>
        <input ref="fileInput" type="file" accept=".json,application/json" style="display:none" @change="onImportFile" />
      </div>
      <div class="side-tabs">
        <span :class="{on: sideTab==='collections'}" @click="sideTab='collections'">Collections</span>
        <span :class="{on: sideTab==='history'}" @click="sideTab='history'">History</span>
      </div>

      <!-- 集合树 -->
      <div v-show="sideTab==='collections'" class="side-scroll">
        <div v-if="!collections.length" class="side-empty">暂无集合，点「＋集合」创建</div>
        <div v-for="col in collections" :key="col.id" class="col-group">
          <div class="col-head" @click="col.expanded = !col.expanded">
            <span class="caret">{{ col.expanded ? '▾' : '▸' }}</span>
            <span class="folder-ico">📁</span>
            <span class="col-name" :title="col.name">{{ col.name }}</span>
            <span class="col-count">{{ col.requests.length }}</span>
            <button class="mini" title="运行整个集合（按顺序传递变量）" @click.stop="runCollection(col)">▶</button>
            <button class="mini" title="重命名" @click.stop="renameCollection(col)">✎</button>
            <button class="mini danger" title="删除" @click.stop="removeCollection(col)">×</button>
          </div>
          <div v-if="col.expanded" class="req-tree">
            <div v-for="req in col.requests" :key="req.id"
                 class="req-item" :class="{active: activeRequestId===req.id}"
                 @click="openRequest(col, req)">
              <span class="method-dot" :class="req.method.toLowerCase()">{{ shortMethod(req.method) }}</span>
              <span class="req-name" :title="req.name || req.url">{{ req.name || req.url || '未命名请求' }}</span>
              <button class="mini" title="重命名" @click.stop="renameRequest(col, req)">✎</button>
              <button class="mini danger" title="删除" @click.stop="removeRequest(col, req)">×</button>
            </div>
            <div class="add-req" @click="newRequest(col)">＋ 新建请求</div>
          </div>
        </div>
      </div>

      <!-- 历史 -->
      <div v-show="sideTab==='history'" class="side-scroll">
        <div class="history-head">
          <span>最近 {{ history.length }} 条</span>
          <button class="mini" @click="clearHistory">清空</button>
        </div>
        <div v-if="!history.length" class="side-empty">还没有发送过请求</div>
        <div v-for="h in history" :key="h.id" class="history-item" @click="loadHistory(h)">
          <div class="history-line">
            <span class="method-dot" :class="h.method.toLowerCase()">{{ shortMethod(h.method) }}</span>
            <span class="history-url" :title="h.url">{{ shortUrl(h.url) }}</span>
          </div>
          <div class="history-meta">
            <span :class="h.status_code && h.status_code<400 ? 'ok':'no'">{{ h.status_code || 'ERR' }}</span>
            <span>{{ h.duration_ms }}ms</span>
            <span>{{ h.time }}</span>
          </div>
        </div>
      </div>

      <!-- 环境 -->
      <div class="env-box">
        <div class="env-line">
          <span class="env-label">Environment</span>
          <select v-model="activeEnvId" class="env-select">
            <option value="">No Environment</option>
            <option v-for="e in environments" :key="e.id" :value="e.id">{{ e.name }}</option>
          </select>
          <button class="mini" title="查看变量" @click="showVars = !showVars">👁</button>
        </div>
        <div v-if="showVars" class="var-quick">
          <div class="var-quick-head">
            <span>变量（环境 + 本地）</span>
            <button class="mini" @click="showVarEditor = true">编辑</button>
          </div>
          <div v-for="(v,k) in effectiveVars" :key="k" class="var-quick-row">
            <code>{{ k }}</code><span>{{ fmtVal(v) }}</span>
          </div>
          <div v-if="!Object.keys(effectiveVars).length" class="muted" style="font-size:11px">暂无变量</div>
        </div>
      </div>
    </aside>

    <!-- ============ 右侧：请求 + 响应 ============ -->
    <main class="pm-main">
      <!-- 请求栏 -->
      <div class="request-bar">
        <select v-model="current.method" class="method-select" :class="current.method.toLowerCase()">
          <option v-for="m in methods" :key="m">{{ m }}</option>
        </select>
        <input v-model="current.url" class="url-input" placeholder="https://api.example.com/v1/resource  （支持 {{变量}}）"
               @keyup.enter="send" />
        <button class="send-btn" :disabled="loading" @click="send">{{ loading ? 'Sending…' : 'Send' }}</button>
        <button class="save-btn" title="保存到集合" @click="saveRequest">Save</button>
        <button class="run-btn" title="运行当前集合的全部请求" @click="runCollection(activeCollection)">Run Collection</button>
      </div>

      <div class="pm-work">
        <!-- 请求配置 -->
        <section class="request-pane">
          <div class="pane-tabs">
            <span v-for="t in requestTabs" :key="t.key" :class="{on: reqTab===t.key}" @click="reqTab=t.key">
              {{ t.label }}<i v-if="tabCount(t.key)">{{ tabCount(t.key) }}</i>
            </span>
          </div>
          <div class="pane-body">
            <!-- Params -->
            <div v-if="reqTab==='params'">
              <div class="tip">查询参数会同步到 URL；修改 URL 中的 query 也会反向同步到这里。</div>
              <table class="kv-table">
                <thead><tr><th style="width:34px"></th><th>Key</th><th>Value</th><th style="width:130px">Description</th><th style="width:52px"></th></tr></thead>
                <tbody>
                  <tr v-for="(p,i) in current.params" :key="i">
                    <td><input type="checkbox" v-model="p.enabled" @change="syncUrlFromParams" /></td>
                    <td><input v-model="p.key" class="cell-input" placeholder="key" @input="syncUrlFromParams" /></td>
                    <td><input v-model="p.value" class="cell-input" placeholder="value" @input="syncUrlFromParams" /></td>
                    <td><input v-model="p.desc" class="cell-input" placeholder="description" /></td>
                    <td><button class="mini danger" @click="current.params.splice(i,1); syncUrlFromParams()">×</button></td>
                  </tr>
                </tbody>
              </table>
              <button class="add-row" @click="current.params.push({key:'',value:'',enabled:true,desc:''})">＋ Add Param</button>
              <div class="bulk-line">
                <button class="mini" @click="bulkEdit('params')">Bulk Edit</button>
                <span class="muted">也可用 <code>&#8fa9ff;&#8fa9ff;变量名&#8fa9ff;&#8fa9ff;</code></span>
              </div>
            </div>

            <!-- Authorization -->
            <div v-if="reqTab==='auth'">
              <div class="field-line">
                <label>Type</label>
                <select v-model="current.auth.type" class="small-select">
                  <option value="none">No Auth</option>
                  <option value="basic">Basic Auth</option>
                  <option value="bearer">Bearer Token</option>
                  <option value="apikey">API Key</option>
                </select>
              </div>
              <div v-if="current.auth.type==='basic'" class="auth-block">
                <div class="field-line"><label>Username</label><input v-model="current.auth.username" class="cell-input" /></div>
                <div class="field-line"><label>Password</label><input v-model="current.auth.password" type="password" class="cell-input" /></div>
              </div>
              <div v-else-if="current.auth.type==='bearer'" class="auth-block">
                <div class="field-line"><label>Token</label><input v-model="current.auth.token" class="cell-input" placeholder="&#8fa9ff;&#8fa9ff;token&#8fa9ff;&#8fa9ff;" /></div>
              </div>
              <div v-else-if="current.auth.type==='apikey'" class="auth-block">
                <div class="field-line"><label>Key</label><input v-model="current.auth.apiKey" class="cell-input" placeholder="X-API-Key" /></div>
                <div class="field-line"><label>Value</label><input v-model="current.auth.apiValue" class="cell-input" /></div>
                <div class="field-line"><label>Add to</label>
                  <select v-model="current.auth.in" class="small-select"><option value="header">Header</option><option value="query">Query Params</option></select>
                </div>
              </div>
              <div v-else class="tip">此请求不使用授权。认证信息会在发送时自动加到请求头 / 查询参数。</div>
            </div>

            <!-- Headers -->
            <div v-if="reqTab==='headers'">
              <div class="tip">请求头会自动带入变量渲染；授权标签页生成的头会合并到这里（同名以生成的为准）。</div>
              <table class="kv-table">
                <thead><tr><th style="width:34px"></th><th>Key</th><th>Value</th><th style="width:52px"></th></tr></thead>
                <tbody>
                  <tr v-for="(h,i) in current.headers" :key="i">
                    <td><input type="checkbox" v-model="h.enabled" /></td>
                    <td><input v-model="h.key" class="cell-input" placeholder="Header" /></td>
                    <td><input v-model="h.value" class="cell-input" placeholder="value" /></td>
                    <td><button class="mini danger" @click="current.headers.splice(i,1)">×</button></td>
                  </tr>
                </tbody>
              </table>
              <button class="add-row" @click="current.headers.push({key:'',value:'',enabled:true})">＋ Add Header</button>
              <div class="bulk-line">
                <button class="mini" @click="bulkEdit('headers')">Bulk Edit</button>
              </div>
            </div>

            <!-- Body -->
            <div v-if="reqTab==='body'">
              <div class="body-modes">
                <label v-for="m in bodyModes" :key="m.value" :class="{on: current.bodyMode===m.value}">
                  <input type="radio" :value="m.value" v-model="current.bodyMode" /> {{ m.label }}
                </label>
              </div>
              <div v-if="current.bodyMode==='none'" class="tip">此请求不发送请求体。</div>
              <div v-else-if="current.bodyMode==='raw'">
                <div class="raw-tools">
                  <select v-model="current.rawLang" class="small-select">
                    <option>JSON</option><option>Text</option><option>XML</option><option>HTML</option><option>JavaScript</option>
                  </select>
                  <button class="mini" @click="beautifyBody">Beautify</button>
                  <span class="muted">支持 &#8fa9ff;&#8fa9ff;变量&#8fa9ff;&#8fa9ff;</span>
                </div>
                <textarea v-model="current.body" class="code-editor" spellcheck="false"
                          placeholder='{ "key": "value" }'></textarea>
              </div>
              <div v-else>
                <div class="tip">{{ current.bodyMode==='form-data' ? 'multipart/form-data（httpx files）' : 'application/x-www-form-urlencoded' }}</div>
                <table class="kv-table">
                  <thead><tr><th style="width:34px"></th><th>Key</th><th>Value</th><th style="width:90px">Type</th><th style="width:52px"></th></tr></thead>
                  <tbody>
                    <tr v-for="(f,i) in current.formData" :key="i">
                      <td><input type="checkbox" v-model="f.enabled" /></td>
                      <td><input v-model="f.key" class="cell-input" placeholder="key" /></td>
                      <td><input v-model="f.value" class="cell-input" placeholder="value" /></td>
                      <td><select v-model="f.type" class="cell-select"><option>text</option><option>file</option></select></td>
                      <td><button class="mini danger" @click="current.formData.splice(i,1)">×</button></td>
                    </tr>
                  </tbody>
                </table>
                <button class="add-row" @click="current.formData.push({key:'',value:'',type:'text',enabled:true})">＋ Add Field</button>
              </div>
            </div>

            <!-- Tests: 断言 + 提取 -->
            <div v-if="reqTab==='tests'">
              <div class="sub-head">
                <span>测试断言（Tests）</span>
                <button class="mini" @click="current.assertions.push({type:'status',op:'eq',key:'',value:'200'})">＋ Add Assertion</button>
              </div>
              <div v-for="(a,i) in current.assertions" :key="i" class="rule-row">
                <select v-model="a.type" class="cell-select"><option value="status">Status code</option><option value="json">JSON field</option><option value="header">Header</option><option value="body">Body contains</option><option value="contains">Contains</option></select>
                <input v-if="a.type==='json'||a.type==='header'" v-model="a.key" class="cell-input" placeholder="data.token" />
                <select v-model="a.op" class="cell-select">
                  <option value="eq">=</option><option value="ne">≠</option><option value="contains">contains</option>
                  <option value="gt">&gt;</option><option value="gte">≥</option><option value="lt">&lt;</option><option value="lte">≤</option>
                  <option value="exists">exists</option><option value="regex">regex</option>
                </select>
                <input v-model="a.value" class="cell-input" placeholder="expected" />
                <button class="mini danger" @click="current.assertions.splice(i,1)">×</button>
              </div>
              <div v-if="!current.assertions.length" class="tip">暂无断言。执行后会显示每条断言的通过情况。</div>

              <div class="sub-head" style="margin-top:18px">
                <span>变量提取（Extract）→ 传给后续请求</span>
                <button class="mini" @click="current.extractors.push({name:'',source:'json',key:''})">＋ Add Extractor</button>
              </div>
              <div v-for="(e,i) in current.extractors" :key="i" class="rule-row">
                <input v-model="e.name" class="cell-input" style="width:120px" placeholder="变量名，如 token" />
                <select v-model="e.source" class="cell-select"><option value="json">JSON field</option><option value="header">Header</option><option value="body">Body</option><option value="status">Status</option></select>
                <input v-if="e.source==='json'||e.source==='header'" v-model="e.key" class="cell-input" placeholder="data.token" />
                <span v-else class="muted" style="font-size:11px">（整段值）</span>
                <button class="mini danger" @click="current.extractors.splice(i,1)">×</button>
              </div>
            </div>
          </div>
        </section>

        <!-- 响应 -->
        <section class="response-pane">
          <div class="resp-head">
            <div class="resp-tabs">
              <span v-for="t in responseTabs" :key="t.key" :class="{on: respTab===t.key}" @click="respTab=t.key">{{ t.label }}</span>
            </div>
            <div v-if="response.status_code" class="resp-meta">
              <span class="status-pill" :class="response.status_code<400?'ok':'no'">{{ response.status_code }} {{ statusText(response.status_code) }}</span>
              <span>{{ response.duration_ms }} ms</span>
              <span>{{ fmtSize(response.size) }}</span>
            </div>
          </div>
          <div class="resp-body">
            <div v-if="loading" class="resp-placeholder">Sending request…</div>
            <div v-else-if="response.error && !response.status_code" class="resp-error">⚠️ {{ response.error }}</div>
            <div v-else-if="!response.status_code && !chainResults.length" class="resp-placeholder">
              <div class="ph-ico">📡</div>
              配置请求后点击 <b>Send</b>，或在左侧集合上点击 <b>▶</b> 运行整个接口链
            </div>

            <!-- Body -->
            <template v-if="respTab==='body' && response.status_code">
              <div class="body-tools">
                <div class="seg">
                  <span v-for="v in ['Pretty','Raw','Preview']" :key="v" :class="{on: bodyView===v}" @click="bodyView=v">{{ v }}</span>
                </div>
                <button class="mini" @click="copyText(prettyBody)">Copy</button>
                <span class="muted">{{ bodyKind }}</span>
              </div>
              <pre v-if="bodyView!=='Preview'" class="resp-code">{{ bodyView==='Pretty' ? prettyBody : rawBody }}</pre>
              <iframe v-else class="resp-preview" sandbox="allow-same-origin" :srcdoc="rawBody"></iframe>
            </template>

            <!-- Headers -->
            <div v-else-if="respTab==='headers' && response.status_code" class="resp-table-wrap">
              <table class="kv-table readonly">
                <thead><tr><th>Key</th><th>Value</th></tr></thead>
                <tbody><tr v-for="(v,k) in response.headers" :key="k"><td><code>{{ k }}</code></td><td>{{ v }}</td></tr></tbody>
              </table>
            </div>

            <!-- Cookies -->
            <div v-else-if="respTab==='cookies' && response.status_code">
              <div v-if="Object.keys(response.cookies||{}).length" class="resp-table-wrap">
                <table class="kv-table readonly">
                  <thead><tr><th>Name</th><th>Value</th></tr></thead>
                  <tbody><tr v-for="(v,k) in response.cookies" :key="k"><td><code>{{ k }}</code></td><td>{{ v }}</td></tr></tbody>
                </table>
              </div>
              <div v-else class="resp-placeholder">响应没有 Cookies</div>
            </div>

            <!-- 断言结果 -->
            <div v-else-if="respTab==='asserts' && response.status_code">
              <div v-if="response.assertions_result?.length" class="assert-list">
                <div v-for="(a,i) in response.assertions_result" :key="i" class="assert-item" :class="a.passed?'ok':'no'">
                  <span class="assert-mark">{{ a.passed?'✓':'✗' }}</span>
                  <div>
                    <div class="assert-title">{{ a.type }}{{ a.key?'.'+a.key:'' }} {{ a.op }} {{ fmtVal(a.expected) }}</div>
                    <div class="assert-detail">实际：{{ fmtVal(a.actual) }}</div>
                  </div>
                </div>
              </div>
              <div v-else class="resp-placeholder">没有配置断言</div>
              <div v-if="Object.keys(response.extracted||{}).length" class="extract-result">
                <div class="extract-title">🔗 已提取到变量池</div>
                <div v-for="(v,k) in response.extracted" :key="k" class="var-quick-row"><code>{{ k }}</code><span>{{ fmtVal(v) }}</span></div>
              </div>
            </div>

            <!-- 接口链结果 -->
            <div v-else-if="chainResults.length" class="chain-results">
              <div v-for="r in chainResults" :key="r.index" class="chain-card">
                <div class="chain-card-head" @click="toggleChain(r.index)">
                  <span class="status-pill" :class="r.status==='passed'?'ok':'no'">{{ r.status_code||'ERR' }}</span>
                  <b>{{ r.index }}. {{ r.method }} {{ shortUrl(r.url) }}</b>
                  <span class="muted">{{ r.duration_ms }}ms</span>
                  <span class="muted" style="margin-left:auto">{{ expandedChain[r.index] ? '收起' : '展开' }}</span>
                </div>
                <div v-if="expandedChain[r.index]" class="chain-card-body">
                  <div v-if="r.error" class="resp-error">⚠️ {{ r.error }}</div>
                  <div class="chain-section"><label>实际请求</label><pre class="resp-code">{{ r.request_info.method }} {{ r.request_info.url }}{{ r.request_info.headers && Object.keys(r.request_info.headers).length ? '\n\nheaders: '+fmt(r.request_info.headers) : '' }}{{ r.request_info.body ? '\n\n'+r.request_info.body : '' }}</pre></div>
                  <div class="chain-section"><label>响应</label><pre class="resp-code">{{ fmt(r.body) }}</pre></div>
                  <div v-if="Object.keys(r.extracted||{}).length" class="chain-section"><label>🔗 提取并传给后续</label><pre class="resp-code">{{ fmt(r.extracted) }}</pre></div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- 变量编辑器弹窗 -->
    <div v-if="showVarEditor" class="modal-mask" @click.self="showVarEditor=false">
      <div class="modal">
        <div class="modal-head">编辑本地变量 <button class="close-x" @click="showVarEditor=false">×</button></div>
        <div class="modal-body">
          <div class="tip">本地变量与环境变合同名时，这里的值优先。执行提取变量也会写入这里。</div>
          <div v-for="(v,k) in varsPool" :key="k" class="rule-row">
            <input class="cell-input" :value="k" readonly style="width:150px" />
            <input class="cell-input" :value="fmtVal(v)" @change="updateVar(k, $event.target.value)" />
            <button class="mini danger" @click="deleteVar(k)">×</button>
          </div>
          <div class="rule-row" style="margin-top:10px">
            <input v-model="newVarKey" class="cell-input" placeholder="变量名" style="width:150px" />
            <input v-model="newVarVal" class="cell-input" placeholder="变量值" />
            <button class="mini" @click="addVar">＋ 添加</button>
          </div>
        </div>
        <div class="modal-foot"><button class="btn" @click="showVarEditor=false">关闭</button></div>
      </div>
    </div>

    <!-- Bulk edit 弹窗 -->
    <div v-if="bulkTarget" class="modal-mask" @click.self="bulkTarget=''">
      <div class="modal">
        <div class="modal-head">批量编辑 {{ bulkTarget==='headers' ? 'Headers' : 'Params' }} <button class="close-x" @click="bulkTarget=''">×</button></div>
        <div class="modal-body">
          <div class="tip">每行一条：<code>Key: Value</code>。空行以 <code>#</code> 开头会被忽略。</div>
          <textarea v-model="bulkText" class="code-editor" style="height:260px" spellcheck="false"></textarea>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="bulkTarget=''">取消</button>
          <button class="btn btn-primary" @click="applyBulk">应用</button>
        </div>
      </div>
    </div>

    <!-- 导出 Postman 集合弹窗 -->
    <div v-if="showExport" class="modal-mask" @click.self="showExport=false">
      <div class="modal wide">
        <div class="modal-head">导出集合（Postman Collection v2.1）<button class="close-x" @click="showExport=false">×</button></div>
        <div class="modal-body">
          <div class="tip">导出为 Postman 标准集合 JSON，可直接导入 Postman 或本平台。断言 / 提取规则等平台特有字段保存在 <code>x-tef</code> 扩展中，重新导入不会丢失。</div>
          <div class="field-line">
            <label>导出范围</label>
            <select v-model="exportScope" class="small-select">
              <option value="current">当前集合：{{ activeCollection?.name || '—' }}</option>
              <option value="all">全部集合（{{ collections.length }} 个，分别下载）</option>
            </select>
          </div>
          <div class="export-preview-title">预览</div>
          <pre class="export-code">{{ exportPreview }}</pre>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="showExport=false">取消</button>
          <button class="btn btn-primary" @click="doExport">⇧ 导出下载</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { api, notify } from '../api'

const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const bodyModes = [
  { value: 'none', label: 'none' },
  { value: 'raw', label: 'raw' },
  { value: 'form-data', label: 'form-data' },
  { value: 'x-www-form-urlencoded', label: 'x-www-form-urlencoded' },
]
const requestTabs = [
  { key: 'params', label: 'Params' },
  { key: 'auth', label: 'Authorization' },
  { key: 'headers', label: 'Headers' },
  { key: 'body', label: 'Body' },
  { key: 'tests', label: 'Tests' },
]
const responseTabs = [
  { key: 'body', label: 'Body' },
  { key: 'headers', label: 'Headers' },
  { key: 'cookies', label: 'Cookies' },
  { key: 'asserts', label: 'Test Results' },
]

let seq = Date.now()
const uid = () => ++seq

function blankRequest(over = {}) {
  return {
    id: uid(), name: '', method: 'GET', url: '',
    params: [], headers: [{ key: 'Content-Type', value: 'application/json', enabled: true }],
    bodyMode: 'raw', rawLang: 'JSON', body: '', formData: [],
    auth: { type: 'none', username: '', password: '', token: '', apiKey: 'X-API-Key', apiValue: '', in: 'header' },
    assertions: [], extractors: [],
    ...over,
  }
}

// ---------- 持久化 ----------
const LS_COLLECTIONS = 'pm_collections_v1'
const LS_HISTORY = 'pm_history_v1'
const LS_VARS = 'api_debug_vars'
const LS_ACTIVE = 'pm_active_v1'

function demoCollections() {
  return [{
    id: uid(), name: 'Demo API', expanded: true,
    requests: [
      blankRequest({
        name: 'Login',
        method: 'POST', url: 'http://127.0.0.1:9001/api/login',
        body: '{\n  "username": "admin",\n  "password": "123456"\n}',
        assertions: [{ type: 'status', op: 'eq', key: '', value: '200' }],
        extractors: [{ name: 'token', source: 'json', key: 'data.token' }],
      }),
      blankRequest({
        name: 'Get User Info',
        method: 'GET', url: 'http://127.0.0.1:9001/api/user/info',
        headers: [{ key: 'Authorization', value: 'Bearer {{token}}', enabled: true }],
        assertions: [{ type: 'status', op: 'eq', key: '', value: '200' }],
      }),
    ],
  }]
}

const collections = ref([])
const history = ref([])
const varsPool = ref({})
const activeEnvId = ref('')
const environments = ref([])
const activeCollectionId = ref(null)
const activeRequestId = ref(null)
const current = ref(blankRequest())
const sideTab = ref('collections')
const reqTab = ref('params')
const respTab = ref('body')
const bodyView = ref('Pretty')
const loading = ref(false)
const response = ref({})
const chainResults = ref([])
const expandedChain = ref({})
const showVars = ref(false)
const showVarEditor = ref(false)
const newVarKey = ref('')
const newVarVal = ref('')
const bulkTarget = ref('')
const bulkText = ref('')
const showExport = ref(false)
const exportScope = ref('current')
const fileInput = ref(null)

const activeCollection = computed(() => collections.value.find(c => c.id === activeCollectionId.value) || null)

function persist() {
  localStorage.setItem(LS_COLLECTIONS, JSON.stringify(collections.value))
  localStorage.setItem(LS_HISTORY, JSON.stringify(history.value))
  localStorage.setItem(LS_VARS, JSON.stringify(varsPool.value))
  localStorage.setItem(LS_ACTIVE, JSON.stringify({ col: activeCollectionId.value, req: activeRequestId.value, env: activeEnvId.value }))
}

onMounted(async () => {
  try {
    collections.value = JSON.parse(localStorage.getItem(LS_COLLECTIONS) || 'null') || demoCollections()
  } catch (e) { collections.value = demoCollections() }
  if (!collections.value.length) collections.value = demoCollections()
  try { history.value = JSON.parse(localStorage.getItem(LS_HISTORY) || '[]') } catch (e) { history.value = [] }
  try { varsPool.value = JSON.parse(localStorage.getItem(LS_VARS) || '{}') } catch (e) { varsPool.value = {} }
  try {
    const a = JSON.parse(localStorage.getItem(LS_ACTIVE) || '{}')
    activeEnvId.value = a.env || ''
    const col = collections.value.find(c => c.id === a.col)
    const req = col?.requests.find(r => r.id === a.req)
    if (col && req) { activeCollectionId.value = col.id; current.value = req; activeRequestId.value = req.id }
    else { activeCollectionId.value = collections.value[0].id; current.value = collections.value[0].requests[0] || blankRequest(); activeRequestId.value = current.value.id }
  } catch (e) {
    activeCollectionId.value = collections.value[0].id
    current.value = collections.value[0].requests[0] || blankRequest()
    activeRequestId.value = current.value.id
  }
  try { environments.value = await api('/api/environments') } catch (e) {}
})

// URL <-> Params 同步
let syncing = false
watch(() => current.value.url, (u) => {
  if (syncing) return
  syncing = true
  current.value.params = parseQuery(u)
  nextTick(() => { syncing = false })
})
function parseQuery(url) {
  const i = (url || '').indexOf('?')
  if (i < 0) return []
  return url.slice(i + 1).split('&').filter(Boolean).map(pair => {
    const idx = pair.indexOf('=')
    const k = idx < 0 ? pair : pair.slice(0, idx)
    const v = idx < 0 ? '' : pair.slice(idx + 1)
    try { return { key: decodeURIComponent(k), value: decodeURIComponent(v), enabled: true, desc: '' } }
    catch (e) { return { key: k, value: v, enabled: true, desc: '' } }
  })
}
function syncUrlFromParams() {
  if (syncing) return
  syncing = true
  const base = (current.value.url || '').split('?')[0]
  const qs = (current.value.params || []).filter(p => p.enabled && p.key)
    .map(p => encodeURIComponent(p.key) + '=' + encodeURIComponent(p.value || '')).join('&')
  current.value.url = base + (qs ? '?' + qs : '')
  nextTick(() => { syncing = false })
  persist()
}

// ---------- 变量 ----------
const activeEnv = computed(() => environments.value.find(e => e.id === activeEnvId.value) || null)
const effectiveVars = computed(() => ({ ...(activeEnv.value?.variables || {}), ...varsPool.value }))
function updateVar(k, val) { varsPool.value[k] = val; persist() }
function addVar() { const k = newVarKey.value.trim(); if (!k) return; varsPool.value[k] = newVarVal.value; newVarKey.value = ''; newVarVal.value = ''; persist() }
function deleteVar(k) { delete varsPool.value[k]; persist() }
function localRender(text) {
  return String(text ?? '').replace(/\{\{\s*([\w.]+)\s*\}\}/g, (m, k) => {
    const v = effectiveVars.value[k]
    return v === undefined ? m : (typeof v === 'object' ? JSON.stringify(v) : String(v))
  })
}

// ---------- 请求构建 ----------
function buildHeaders() {
  const h = {}
  ;(current.value.headers || []).forEach(x => { if (x.enabled && x.key) h[x.key] = x.value })
  const a = current.value.auth || {}
  if (a.type === 'basic') h['Authorization'] = 'Basic ' + btoa(unescape(encodeURIComponent(localRender(a.username) + ':' + localRender(a.password))))
  else if (a.type === 'bearer') h['Authorization'] = 'Bearer ' + localRender(a.token)
  else if (a.type === 'apikey' && a.in === 'header') h[a.apiKey || 'X-API-Key'] = localRender(a.apiValue)
  return h
}
function buildParams() {
  const p = []
  ;(current.value.params || []).forEach(x => { if (x.enabled && x.key) p.push({ key: x.key, value: x.value }) })
  const a = current.value.auth || {}
  if (a.type === 'apikey' && a.in === 'query') p.push({ key: a.apiKey || 'X-API-Key', value: localRender(a.apiValue) })
  return p
}
function toCase(req) {
  const base = (req.url || '').split('?')[0]
  const extra = buildParamsFor(req)
  const qs = extra.map(p => encodeURIComponent(p.key) + '=' + encodeURIComponent(p.value || '')).join('&')
  return {
    name: req.name, method: req.method,
    url: base + (qs ? '?' + qs : ''),
    headers: buildHeadersFor(req),
    body: req.bodyMode === 'raw' ? req.body : '',
    body_mode: req.bodyMode,
    form_data: (req.formData || []).map(f => ({ key: f.key, value: f.value, type: f.type, enabled: f.enabled })),
    assertions: req.assertions || [], extractors: req.extractors || [],
  }
}
function buildHeadersFor(req) {
  const h = {}
  ;(req.headers || []).forEach(x => { if (x.enabled && x.key) h[x.key] = x.value })
  const a = req.auth || {}
  if (a.type === 'basic') h['Authorization'] = 'Basic ' + btoa(unescape(encodeURIComponent(localRender(a.username) + ':' + localRender(a.password))))
  else if (a.type === 'bearer') h['Authorization'] = 'Bearer ' + localRender(a.token)
  else if (a.type === 'apikey' && a.in === 'header') h[a.apiKey || 'X-API-Key'] = localRender(a.apiValue)
  return h
}
function buildParamsFor(req) {
  const p = []
  ;(req.params || []).forEach(x => { if (x.enabled && x.key) p.push({ key: x.key, value: x.value }) })
  const a = req.auth || {}
  if (a.type === 'apikey' && a.in === 'query') p.push({ key: a.apiKey || 'X-API-Key', value: localRender(a.apiValue) })
  return p
}

async function send() {
  if (!current.value.url.trim()) { notify('请填写请求 URL', 'error'); return }
  loading.value = true; response.value = {}; chainResults.value = []
  respTab.value = 'body'; bodyView.value = 'Pretty'
  const snapshot = JSON.parse(JSON.stringify(current.value))
  try {
    const c = toCase(current.value)
    const envVars = activeEnv.value?.variables || {}
    const r = await api('/api/debug/run', { method: 'POST', body: { ...c, variables: { ...envVars, ...varsPool.value } } })
    response.value = r
    if (Object.keys(r.extracted || {}).length) {
      Object.assign(varsPool.value, Object.fromEntries(Object.entries(r.extracted).filter(([, v]) => v !== null)))
      persist()
    }
    history.value.unshift({ id: uid(), method: c.method, url: c.url, status_code: r.status_code, duration_ms: r.duration_ms, time: new Date().toLocaleTimeString('zh-CN', { hour12: false }), snapshot })
    history.value = history.value.slice(0, 50)
    persist()
    if (r.error && !r.status_code) notify(r.error, 'error')
    else if (r.assertions_result?.some(a => !a.passed)) notify('存在未通过的断言', 'error')
    else notify(`HTTP ${r.status_code} · ${r.duration_ms}ms`)
  } catch (e) { response.value = { error: e.message }; notify('请求失败：' + e.message, 'error') }
  finally { loading.value = false }
}

async function runCollection(col) {
  if (!col || !col.requests.length) { notify('集合中没有请求', 'error'); return }
  loading.value = true; response.value = {}; chainResults.value = []; respTab.value = 'body'
  try {
    const steps = col.requests.map(toCase)
    const r = await api('/api/debug/run-chain', { method: 'POST', body: { steps, variables: { ...(activeEnv.value?.variables || {}), ...varsPool.value } } })
    chainResults.value = r.results
    varsPool.value = { ...varsPool.value, ...(r.variables || {}) }
    persist()
    notify(`接口链完成：${r.results.filter(x => x.status === 'passed').length}/${r.results.length} 通过`)
  } catch (e) { notify('执行失败：' + e.message, 'error') }
  finally { loading.value = false }
}

// ---------- 集合操作 ----------
function newCollection() {
  const name = prompt('集合名称', 'New Collection')
  if (!name) return
  const col = { id: uid(), name, expanded: true, requests: [] }
  collections.value.push(col); activeCollectionId.value = col.id
  current.value = blankRequest(); activeRequestId.value = current.value.id
  persist()
}
function renameCollection(col) { const n = prompt('重命名集合', col.name); if (n) { col.name = n; persist() } }
function removeCollection(col) {
  if (!confirm(`删除集合「${col.name}」及其所有请求？`)) return
  collections.value = collections.value.filter(c => c.id !== col.id)
  if (activeCollectionId.value === col.id) {
    activeCollectionId.value = collections.value[0]?.id || null
    current.value = collections.value[0]?.requests[0] || blankRequest()
    activeRequestId.value = current.value.id
  }
  persist()
}
function newRequest(col = activeCollection.value) {
  if (!col) { notify('请先创建一个集合', 'error'); return }
  const req = blankRequest({ name: 'New Request' })
  col.requests.push(req); activeCollectionId.value = col.id
  current.value = req; activeRequestId.value = req.id; sideTab.value = 'collections'
  persist()
}
function openRequest(col, req) {
  activeCollectionId.value = col.id; activeRequestId.value = req.id
  current.value = req; response.value = {}; chainResults.value = []
}
function renameRequest(col, req) { const n = prompt('请求名称', req.name); if (n !== null) { req.name = n; persist() } }
function removeRequest(col, req) {
  if (!confirm(`删除请求「${req.name || req.url}」？`)) return
  col.requests = col.requests.filter(r => r.id !== req.id)
  if (activeRequestId.value === req.id) {
    current.value = col.requests[0] || blankRequest(); activeRequestId.value = current.value.id
  }
  persist()
}
function saveRequest() {
  if (activeCollection.value && activeRequestId.value) {
    const idx = activeCollection.value.requests.findIndex(r => r.id === activeRequestId.value)
    if (idx >= 0) { activeCollection.value.requests[idx] = current.value }
    else activeCollection.value.requests.push(current.value)
  } else if (activeCollection.value) {
    activeCollection.value.requests.push(current.value); activeRequestId.value = current.value.id
  } else { newCollection(); return }
  persist(); notify('已保存到集合')
}
function loadHistory(h) {
  current.value = JSON.parse(JSON.stringify(h.snapshot))
  activeRequestId.value = null; response.value = {}; chainResults.value = []
  sideTab.value = 'collections'; notify('已载入历史请求')
}
function clearHistory() { if (confirm('清空历史记录？')) { history.value = []; persist() } }

// ---------- Postman 集合导入 / 导出 ----------
const PM_SCHEMA = 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'

function requestToPostmanItem(req) {
  const rawUrl = req.url || ''
  const pmUrl = { raw: rawUrl }
  try {
    const u = new URL(rawUrl)
    pmUrl.protocol = u.protocol.replace(':', '')
    pmUrl.host = u.hostname.split('.')
    if (u.port) pmUrl.port = u.port
    pmUrl.path = u.pathname.split('/').filter(Boolean)
    if (u.search) pmUrl.query = [...u.searchParams].map(([k, v]) => ({ key: k, value: v }))
  } catch (e) { /* 含 {{变量}} 的 URL 无法解析，仅保留 raw */ }
  const query = pmUrl.query || []
  ;(req.params || []).forEach(p => {
    if (p.enabled && p.key && !query.some(q => q.key === p.key)) query.push({ key: p.key, value: p.value, description: p.desc })
  })
  if (query.length) pmUrl.query = query

  const item = {
    name: req.name || `${req.method} Request`,
    request: {
      method: req.method,
      header: (req.headers || []).filter(h => h.enabled && h.key).map(h => ({ key: h.key, value: h.value, type: 'text' })),
      url: pmUrl,
      description: '',
    },
    response: [],
  }
  const a = req.auth || {}
  if (a.type === 'bearer') item.request.auth = { type: 'bearer', bearer: [{ key: 'token', value: a.token || '', type: 'string' }] }
  else if (a.type === 'basic') item.request.auth = { type: 'basic', basic: [{ key: 'username', value: a.username || '', type: 'string' }, { key: 'password', value: a.password || '', type: 'string' }] }
  else if (a.type === 'apikey') item.request.auth = { type: 'apikey', apikey: [{ key: 'key', value: a.apiKey || 'X-API-Key', type: 'string' }, { key: 'value', value: a.apiValue || '', type: 'string' }, { key: 'in', value: a.in || 'header', type: 'string' }] }

  if (req.bodyMode === 'raw' && req.body) {
    item.request.body = { mode: 'raw', raw: req.body, options: { raw: { language: (req.rawLang || 'JSON').toLowerCase() } } }
  } else if (req.bodyMode === 'form-data') {
    item.request.body = { mode: 'formdata', formdata: (req.formData || []).filter(f => f.enabled && f.key).map(f => ({ key: f.key, value: f.value, type: f.type === 'file' ? 'file' : 'text' })) }
  } else if (req.bodyMode === 'x-www-form-urlencoded') {
    item.request.body = { mode: 'urlencoded', urlencoded: (req.formData || []).filter(f => f.enabled && f.key).map(f => ({ key: f.key, value: f.value })) }
  }
  // Postman 允许的 x- 私有扩展：保留平台特有字段，round-trip 不丢失
  item['x-tef'] = {
    bodyMode: req.bodyMode, rawLang: req.rawLang,
    params: req.params || [], formData: req.formData || [],
    assertions: req.assertions || [], extractors: req.extractors || [], auth: a,
  }
  return item
}

function collectionToPostman(col) {
  return {
    info: {
      name: col.name,
      description: 'Exported from 测试提效平台 · API Workbench',
      schema: PM_SCHEMA,
    },
    item: (col.requests || []).map(requestToPostmanItem),
    variable: [],
  }
}

function postmanItemToRequest(item) {
  const r = item.request || {}
  let url = '', params = []
  const pu = r.url
  if (typeof pu === 'string') url = pu
  else if (pu && typeof pu === 'object') {
    url = pu.raw || ''
    if (!url && pu.host) url = (pu.protocol ? pu.protocol + '://' : '') + (Array.isArray(pu.host) ? pu.host.join('.') : pu.host) + (pu.port ? ':' + pu.port : '') + (Array.isArray(pu.path) ? '/' + pu.path.join('/') : '')
    if (Array.isArray(pu.query)) params = pu.query.map(q => ({ key: q.key || '', value: q.value || '', enabled: !q.disabled, desc: q.description || '' }))
  }
  const headers = Array.isArray(r.header) && r.header.length
    ? r.header.map(h => ({ key: h.key || '', value: h.value || '', enabled: !h.disabled }))
    : [{ key: 'Content-Type', value: 'application/json', enabled: true }]
  let bodyMode = 'raw', rawLang = 'JSON', body = '', formData = []
  const b = r.body || {}
  if (b.mode === 'raw') {
    bodyMode = 'raw'; body = b.raw || ''
    const lang = (b.options?.raw?.language || 'json').toLowerCase()
    rawLang = lang.charAt(0).toUpperCase() + lang.slice(1)
  } else if (b.mode === 'formdata') {
    bodyMode = 'form-data'
    formData = (b.formdata || []).map(f => ({ key: f.key || '', value: f.value || '', type: f.type === 'file' ? 'file' : 'text', enabled: !f.disabled }))
  } else if (b.mode === 'urlencoded') {
    bodyMode = 'x-www-form-urlencoded'
    formData = (b.urlencoded || []).map(f => ({ key: f.key || '', value: f.value || '', type: 'text', enabled: !f.disabled }))
  } else bodyMode = 'none'

  const auth = { type: 'none', username: '', password: '', token: '', apiKey: 'X-API-Key', apiValue: '', in: 'header' }
  const pa = r.auth || {}
  const pick = (arr, k) => (arr || []).find(x => x.key === k)?.value || ''
  if (pa.type === 'bearer') { auth.type = 'bearer'; auth.token = pick(pa.bearer, 'token') }
  else if (pa.type === 'basic') { auth.type = 'basic'; auth.username = pick(pa.basic, 'username'); auth.password = pick(pa.basic, 'password') }
  else if (pa.type === 'apikey') { auth.type = 'apikey'; auth.apiKey = pick(pa.apikey, 'key') || 'X-API-Key'; auth.apiValue = pick(pa.apikey, 'value'); auth.in = pick(pa.apikey, 'in') || 'header' }

  const tef = item['x-tef'] || {}
  return blankRequest({
    name: item.name || '', method: r.method || 'GET', url,
    params: tef.params || params, headers,
    bodyMode: tef.bodyMode || bodyMode, rawLang: tef.rawLang || rawLang,
    body, formData: tef.formData || formData, auth: tef.auth || auth,
    assertions: tef.assertions || [], extractors: tef.extractors || [],
  })
}

function collectPostmanItems(items, out, prefix = '') {
  ;(items || []).forEach(it => {
    if (it.request) out.push(postmanItemToRequest(it))
    else if (Array.isArray(it.item)) collectPostmanItems(it.item, out, it.name ? prefix + it.name + ' / ' : prefix)
  })
}

function postmanToCollections(data) {
  const docs = Array.isArray(data) ? data : [data]
  const out = []
  docs.forEach(doc => {
    if (!doc || !doc.info || !Array.isArray(doc.item)) return
    const reqs = []
    collectPostmanItems(doc.item, reqs)
    out.push({ id: uid(), name: doc.info.name || 'Imported Collection', expanded: true, requests: reqs })
  })
  return out
}

function triggerImport() { if (fileInput.value) fileInput.value.click() }
async function onImportFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    const cols = postmanToCollections(data)
    if (!cols.length) throw new Error('不是有效的 Postman Collection v2.1 文件（缺少 info / item）')
    const total = cols.reduce((n, c) => n + c.requests.length, 0)
    if (!confirm(`导入 ${cols.length} 个集合、共 ${total} 个请求？将追加到现有集合。`)) return
    collections.value.push(...cols)
    activeCollectionId.value = cols[0].id
    current.value = cols[0].requests[0] || blankRequest()
    activeRequestId.value = current.value.id
    sideTab.value = 'collections'
    persist()
    notify(`已导入 ${cols.length} 个集合（${total} 个请求）`)
  } catch (err) { notify('导入失败：' + err.message, 'error') }
}

function downloadJson(obj, filename) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
function safeFileName(name) { return (name || 'collection').replace(/[\\/:*?"<>|]/g, '_') }
const exportPreview = computed(() => {
  const col = exportScope.value === 'all' ? collections.value[0] : activeCollection.value
  if (!col) return '// 暂无集合'
  try { return JSON.stringify(collectionToPostman(col), null, 2) } catch (e) { return '// 预览生成失败：' + e.message }
})
function doExport() {
  if (exportScope.value === 'current') {
    const col = activeCollection.value
    if (!col) { notify('请先选择集合', 'error'); return }
    downloadJson(collectionToPostman(col), safeFileName(col.name) + '.postman_collection.json')
    notify('已导出当前集合')
  } else {
    if (!collections.value.length) { notify('暂无集合', 'error'); return }
    collections.value.forEach((col, i) => setTimeout(() => {
      downloadJson(collectionToPostman(col), safeFileName(col.name) + '.postman_collection.json')
    }, i * 400))
    notify(`已导出 ${collections.value.length} 个集合`)
  }
  showExport.value = false
}

// ---------- 工具 ----------
function bulkEdit(target) {
  bulkTarget.value = target
  const rows = target === 'headers' ? current.value.headers : current.value.params
  bulkText.value = rows.filter(x => x.key).map(x => `${x.key}: ${x.value}`).join('\n')
}
function applyBulk() {
  const rows = bulkText.value.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('//') && !l.startsWith('#'))
    .map(l => { const i = l.indexOf(':'); return i < 0 ? { key: l, value: '', enabled: true } : { key: l.slice(0, i).trim(), value: l.slice(i + 1).trim(), enabled: true } })
  if (bulkTarget.value === 'headers') current.value.headers = rows
  else { current.value.params = rows; nextTick(syncUrlFromParams) }
  bulkTarget.value = ''; persist()
}
function beautifyBody() {
  try { current.value.body = JSON.stringify(JSON.parse(current.value.body), null, 2) }
  catch (e) { notify('不是合法 JSON，无法格式化', 'error') }
}
function tabCount(k) {
  if (k === 'headers') return current.value.headers.filter(h => h.enabled && h.key).length
  if (k === 'params') return current.value.params.filter(p => p.enabled && p.key).length
  if (k === 'tests') return (current.value.assertions?.length || 0) + (current.value.extractors?.length || 0)
  return 0
}
function toggleChain(idx) { expandedChain.value[idx] = !expandedChain.value[idx] }
function shortMethod(m) { return ({ GET: 'GET', POST: 'POST', PUT: 'PUT', PATCH: 'PAT', DELETE: 'DEL', HEAD: 'HEAD', OPTIONS: 'OPT' })[m] || m }
function shortUrl(u) { return u && u.length > 46 ? u.slice(0, 46) + '…' : (u || '') }
function fmt(v) { return typeof v === 'string' ? v : JSON.stringify(v, null, 2) }
function fmtVal(v) { return typeof v === 'object' ? JSON.stringify(v) : String(v ?? '') }
function fmtSize(n) { return !n ? '0 B' : n < 1024 ? n + ' B' : (n / 1024).toFixed(1) + ' KB' }
function statusText(c) { return ({ 200: 'OK', 201: 'Created', 204: 'No Content', 400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found', 500: 'Server Error' })[c] || '' }
async function copyText(text) { try { await navigator.clipboard.writeText(text); notify('已复制') } catch (e) {} }

const prettyBody = computed(() => {
  const b = response.value.body
  if (b == null) return ''
  if (typeof b === 'string') { try { return JSON.stringify(JSON.parse(b), null, 2) } catch (e) { return b } }
  return JSON.stringify(b, null, 2)
})
const rawBody = computed(() => typeof response.value.body === 'string' ? response.value.body : JSON.stringify(response.value.body ?? ''))
const bodyKind = computed(() => {
  const ct = String(response.value.headers?.['content-type'] || '')
  if (ct.includes('json')) return 'JSON'
  if (ct.includes('html')) return 'HTML'
  if (ct.includes('xml')) return 'XML'
  if (ct.includes('javascript')) return 'JavaScript'
  return 'Text'
})
</script>

<style scoped>
.pm-app { display: flex; gap: 0; height: calc(100vh - 118px); min-height: 620px; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); }

/* ---------- 左侧 ---------- */
.pm-side { width: 262px; flex-shrink: 0; background: var(--panel); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
.side-head { padding: 12px 12px 8px; display: flex; align-items: center; justify-content: space-between; }
.side-title { font-weight: 700; font-size: 13px; color: #3a4052; letter-spacing: .3px; }
.side-actions { display: flex; gap: 4px; }
.side-actions .ico-btn { border: 1px solid var(--border); background: var(--panel); border-radius: 5px; padding: 3px 6px; font-size: 11px; color: var(--muted); }
.side-actions .ico-btn:hover { border-color: var(--primary); color: var(--primary); }
.io-bar { display: flex; gap: 4px; padding: 0 12px 8px; }
.io-btn { flex: 1; border: 1px dashed var(--border-strong); background: var(--panel); border-radius: 5px; padding: 5px 4px; font-size: 11px; color: var(--muted); white-space: nowrap; }
.io-btn:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-light); }
.export-preview-title { font-size: 11px; color: var(--muted); margin: 12px 0 5px; font-weight: 600; }
.export-code { background: var(--text); color: #c9d4f5; padding: 12px; border-radius: 7px; font-size: 11px; line-height: 1.5; font-family: Consolas, Monaco, monospace; max-height: 300px; overflow: auto; white-space: pre; margin: 0; }
.side-tabs { display: flex; border-bottom: 1px solid var(--border); padding: 0 10px; }
.side-tabs span { padding: 8px 10px; font-size: 12px; color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; }
.side-tabs span.on { color: var(--primary); border-color: var(--primary); font-weight: 600; }
.side-scroll { flex: 1; overflow: auto; padding: 8px 6px; }
.side-empty { padding: 22px 10px; text-align: center; color: var(--muted); font-size: 12px; }
.col-group { margin-bottom: 4px; }
.col-head { display: flex; align-items: center; gap: 5px; padding: 6px 6px; border-radius: 5px; cursor: pointer; font-size: 12px; }
.col-head:hover { background: var(--panel-2); }
.caret { color: var(--muted); width: 10px; }
.folder-ico { font-size: 12px; }
.col-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.col-count { font-size: 10px; color: var(--muted); background: #e8ebf3; border-radius: 8px; padding: 1px 5px; }
.mini { border: none; background: none; color: #9aa1b2; cursor: pointer; font-size: 12px; padding: 1px 3px; border-radius: 4px; }
.mini:hover { color: var(--primary); background: var(--primary-light); }
.mini.danger:hover { color: var(--danger); background: rgba(235,87,87,.15); }
.req-tree { padding-left: 18px; }
.req-item { display: flex; align-items: center; gap: 5px; padding: 5px 4px; border-radius: 5px; cursor: pointer; font-size: 12px; }
.req-item:hover { background: var(--panel-2); }
.req-item.active { background: #e5ebff; }
.req-item.active .req-name { color: var(--primary); font-weight: 600; }
.method-dot { font-size: 9px; font-weight: 700; padding: 1px 3px; border-radius: 3px; background: var(--primary-light); color: #8fa9ff; min-width: 30px; text-align: center; }
.method-dot.post { background: rgba(226,163,60,.15); color: #e8bd6b; }
.method-dot.put, .method-dot.patch { background: #ede9fe; color: #7c3aed; }
.method-dot.delete { background: rgba(235,87,87,.15); color: var(--danger); }
.req-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.add-req { font-size: 11px; color: var(--muted); padding: 5px 8px; cursor: pointer; }
.add-req:hover { color: var(--primary); }
.history-head { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px 8px; font-size: 11px; color: var(--muted); }
.history-item { padding: 7px 8px; border-radius: 5px; cursor: pointer; }
.history-item:hover { background: var(--panel-2); }
.history-line { display: flex; align-items: center; gap: 6px; }
.history-url { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.history-meta { display: flex; gap: 10px; font-size: 10px; color: var(--muted); margin-top: 3px; padding-left: 36px; }
.history-meta .ok { color: var(--success); }
.history-meta .no { color: var(--danger); }
.env-box { border-top: 1px solid var(--border); padding: 8px 10px; background: var(--panel); }
.env-line { display: flex; align-items: center; gap: 6px; }
.env-label { font-size: 10px; color: var(--muted); text-transform: uppercase; }
.env-select { flex: 1; min-width: 0; border: 1px solid var(--border); border-radius: 5px; padding: 4px 6px; font-size: 11px; background: var(--panel); }
.var-quick { margin-top: 8px; max-height: 170px; overflow: auto; border-top: 1px dashed var(--border); padding-top: 6px; }
.var-quick-head { display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: var(--muted); margin-bottom: 4px; }
.var-quick-row { display: flex; gap: 8px; font-size: 10px; padding: 2px 0; }
.var-quick-row code { color: var(--primary); min-width: 70px; word-break: break-all; }
.var-quick-row span { color: var(--muted); word-break: break-all; }

/* ---------- 右侧 ---------- */
.pm-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.request-bar { display: flex; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--border); background: var(--panel-2); }
.method-select { width: 100px; flex-shrink: 0; border: 1px solid var(--border); border-radius: 6px; padding: 0 8px; font-weight: 700; font-size: 13px; background: var(--panel); color: #8fa9ff; }
.method-select.post { color: #e8bd6b; }
.method-select.put, .method-select.patch { color: #7c3aed; }
.method-select.delete { color: var(--danger); }
.url-input { flex: 1; min-width: 0; border: 1px solid var(--border); border-radius: 6px; padding: 8px 11px; font-size: 13px; font-family: Consolas, monospace; background: var(--panel); }
.url-input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(79,110,247,.12); }
.send-btn, .save-btn, .run-btn { border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 600; border: 1px solid var(--border); background: var(--panel); white-space: nowrap; }
.send-btn { background: var(--primary); border-color: var(--primary); color: #fff; }
.send-btn:hover { background: var(--primary-hover); }
.send-btn:disabled { opacity: .6; }
.save-btn:hover, .run-btn:hover { border-color: var(--primary); color: var(--primary); }
.pm-work { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.request-pane { flex: 0 0 46%; min-height: 200px; display: flex; flex-direction: column; border-bottom: 1px solid var(--border); }
.response-pane { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.pane-tabs, .resp-tabs { display: flex; gap: 2px; padding: 0 12px; border-bottom: 1px solid var(--border); background: var(--panel); flex-shrink: 0; }
.pane-tabs span, .resp-tabs span { padding: 9px 12px; font-size: 12px; color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }
.pane-tabs span.on, .resp-tabs span.on { color: var(--primary); border-color: var(--primary); font-weight: 600; }
.pane-tabs i { font-style: normal; font-size: 9px; background: var(--primary-light); color: var(--primary); border-radius: 8px; padding: 1px 5px; margin-left: 4px; }
.pane-body { flex: 1; overflow: auto; padding: 12px 14px; }
.tip { font-size: 11px; color: var(--muted); margin-bottom: 10px; line-height: 1.6; }
.tip code, .bulk-line code { background: var(--primary-light); color: var(--primary); padding: 1px 4px; border-radius: 3px; }

.kv-table { width: 100%; border-collapse: collapse; }
.kv-table th { font-size: 10px; color: var(--muted); text-align: left; padding: 5px 6px; background: var(--panel-2); border-bottom: 1px solid var(--border); }
.kv-table td { padding: 3px 6px; border-bottom: 1px solid var(--border); }
.cell-input, .cell-select { width: 100%; border: 1px solid transparent; border-radius: 4px; padding: 5px 6px; font-size: 12px; background: transparent; }
.cell-input:hover, .cell-select:hover { border-color: var(--border); background: var(--panel); }
.cell-input:focus, .cell-select:focus { outline: none; border-color: var(--primary); background: var(--panel); }
.cell-select { font-size: 11px; }
.kv-table.readonly td { font-size: 11px; word-break: break-all; }
.add-row { border: none; background: none; color: var(--primary); font-size: 11px; padding: 7px 4px; cursor: pointer; }
.bulk-line { margin-top: 8px; display: flex; align-items: center; gap: 10px; font-size: 11px; }
.field-line { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.field-line label { width: 86px; text-align: right; font-size: 12px; color: var(--muted); }
.field-line .cell-input { border: 1px solid var(--border); max-width: 420px; }
.small-select { border: 1px solid var(--border); border-radius: 5px; padding: 5px 8px; font-size: 12px; background: var(--panel); }
.auth-block { padding: 10px 0 0 96px; }
.body-modes { display: flex; gap: 4px; margin-bottom: 10px; flex-wrap: wrap; }
.body-modes label { font-size: 11px; padding: 5px 9px; border: 1px solid var(--border); border-radius: 5px; cursor: pointer; color: var(--muted); }
.body-modes label.on { background: var(--primary-light); border-color: var(--primary); color: var(--primary); font-weight: 600; }
.body-modes input { display: none; }
.raw-tools { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 11px; }
.code-editor { width: 100%; height: calc(100% - 60px); min-height: 130px; border: 1px solid var(--border); border-radius: 6px; padding: 10px; font-family: Consolas, Monaco, monospace; font-size: 12px; line-height: 1.6; resize: vertical; background: var(--panel); }
.sub-head { display: flex; align-items: center; justify-content: space-between; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
.rule-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.rule-row .cell-input, .rule-row .cell-select { border: 1px solid var(--border); }

.resp-head { display: flex; align-items: center; justify-content: space-between; padding-right: 12px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.resp-meta { display: flex; align-items: center; gap: 12px; font-size: 11px; color: var(--muted); }
.status-pill { padding: 3px 9px; border-radius: 12px; font-size: 11px; font-weight: 700; }
.status-pill.ok { background: rgba(39,166,68,.16); color: var(--success); }
.status-pill.no { background: rgba(235,87,87,.15); color: var(--danger); }
.resp-body { flex: 1; overflow: auto; padding: 10px 14px; min-height: 0; }
.resp-placeholder { text-align: center; color: var(--muted); font-size: 12px; padding: 40px 10px; }
.ph-ico { font-size: 34px; opacity: .5; margin-bottom: 8px; }
.resp-error { background: rgba(235,87,87,.15); color: var(--danger); padding: 10px; border-radius: 6px; font-size: 12px; margin-bottom: 10px; }
.body-tools { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 11px; }
.seg { display: flex; border: 1px solid var(--border); border-radius: 5px; overflow: hidden; }
.seg span { padding: 4px 10px; cursor: pointer; color: var(--muted); }
.seg span.on { background: var(--primary); color: #fff; }
.resp-code { background: var(--text); color: #c9d4f5; padding: 12px; border-radius: 7px; font-size: 11.5px; line-height: 1.6; font-family: Consolas, Monaco, monospace; white-space: pre-wrap; word-break: break-word; margin: 0; }
.resp-preview { width: 100%; height: 100%; min-height: 260px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel); }
.resp-table-wrap { overflow: auto; }
.assert-list { display: flex; flex-direction: column; gap: 6px; }
.assert-item { display: flex; gap: 10px; padding: 8px 10px; border-radius: 6px; font-size: 12px; }
.assert-item.ok { background: rgba(39,166,68,.16); color: var(--success); }
.assert-item.no { background: rgba(235,87,87,.15); color: var(--danger); }
.assert-mark { font-weight: 700; }
.assert-title { font-weight: 600; }
.assert-detail { font-size: 11px; opacity: .8; margin-top: 2px; }
.extract-result { margin-top: 14px; padding: 10px; border: 1px dashed var(--border); border-radius: 6px; }
.extract-title { font-size: 12px; font-weight: 600; margin-bottom: 6px; }
.chain-results { display: flex; flex-direction: column; gap: 8px; }
.chain-card { border: 1px solid var(--border); border-radius: 7px; overflow: hidden; }
.chain-card-head { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: var(--panel-2); cursor: pointer; font-size: 12px; }
.chain-card-body { padding: 10px; border-top: 1px solid var(--border); }
.chain-section { margin-bottom: 10px; }
.chain-section label { display: block; font-size: 11px; color: var(--muted); margin-bottom: 4px; }
</style>
