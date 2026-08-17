import { defineStore } from 'pinia'

export const useTemplateStore = defineStore('template', {
  state: () => ({
    templates: [
      {
        id: 'sys_info',
        name: '系统信息',
        category: '基础管理',
        prompt: '帮我查看系统版本、内核和运行时信息',
        description: '获取系统的基本信息，包括操作系统版本、内核版本等'
      },
      {
        id: 'disk_check',
        name: '磁盘检查',
        category: '基础管理',
        prompt: '帮我检查磁盘使用并指出风险分区',
        description: '检查磁盘使用情况，识别空间不足的分区'
      },
      {
        id: 'net_check',
        name: '网络连通',
        category: '基础管理',
        prompt: '帮我做网络连通性和 DNS 检查',
        description: '测试网络连通性和DNS解析功能'
      },
      {
        id: 'proc_scan',
        name: '进程巡检',
        category: '进程服务',
        prompt: '帮我查看高资源占用进程并排序',
        description: '检查系统中占用资源较高的进程'
      },
      {
        id: 'port_scan',
        name: '端口占用',
        category: '进程服务',
        prompt: '帮我检查端口占用并标记异常',
        description: '检查系统中占用的端口并识别异常情况'
      },
      {
        id: 'service_status',
        name: '服务状态',
        category: '进程服务',
        prompt: '帮我检查 nginx、docker、ssh 服务状态',
        description: '检查常用服务的运行状态'
      },
      {
        id: 'docker_ps',
        name: '容器列表',
        category: 'Docker 容器',
        prompt: '帮我列出所有容器和健康状态',
        description: '查看所有Docker容器及其健康状态'
      },
      {
        id: 'docker_img',
        name: '镜像列表',
        category: 'Docker 容器',
        prompt: '帮我列出镜像并给出清理建议',
        description: '查看Docker镜像并提供清理建议'
      },
      {
        id: 'install_nginx',
        name: '安装 Nginx',
        category: '软件管理',
        prompt: '请在当前系统安装 nginx 并设置开机自启',
        description: '安装Nginx并配置开机自启'
      },
      {
        id: 'install_docker',
        name: '安装 Docker',
        category: '软件管理',
        prompt: '请帮我安装 docker 并验证服务状态',
        description: '安装Docker并验证服务状态'
      },
      {
        id: 'upgrade_all',
        name: '系统升级',
        category: '软件管理',
        prompt: '请更新软件索引并升级系统包',
        description: '更新系统软件包到最新版本'
      },
      {
        id: 'create_user',
        name: '创建用户',
        category: '用户权限',
        prompt: '帮我创建一个新用户并加入 sudo 组，用户名为 devops',
        description: '创建新用户并添加到sudo组'
      },
      {
        id: 'list_login',
        name: '在线用户',
        category: '用户权限',
        prompt: '帮我查看当前登录用户和最近登录记录',
        description: '查看当前登录用户和最近的登录记录'
      },
      {
        id: 'login_fail',
        name: '失败登录检查',
        category: '安全巡检',
        prompt: '帮我检查近期失败登录并统计来源 IP',
        description: '检查近期的失败登录尝试并统计来源IP'
      },
      {
        id: 'fw_check',
        name: '防火墙状态',
        category: '安全巡检',
        prompt: '帮我检查防火墙规则和开放端口',
        description: '检查防火墙规则和当前开放的端口'
      },
      {
        id: 'health',
        name: '一键健康巡检',
        category: '运维自动化',
        prompt: '帮我执行完整健康巡检并输出建议',
        description: '执行全面的系统健康检查并提供优化建议'
      },
      {
        id: 'clean_tmp',
        name: '清理临时文件',
        category: '运维自动化',
        prompt: '帮我安全清理临时文件和无用缓存',
        description: '清理系统临时文件和无用缓存以释放空间'
      }
    ],
    categories: [
      '基础管理',
      '进程服务',
      'Docker 容器',
      '软件管理',
      '用户权限',
      '安全巡检',
      '运维自动化'
    ],
    loading: false,
    error: null
  }),
  getters: {
    getTemplatesByCategory: (state) => (category) => {
      return state.templates.filter(template => template.category === category)
    },
    searchTemplates: (state) => (keyword) => {
      if (!keyword) return state.templates
      const lowerKeyword = keyword.toLowerCase()
      return state.templates.filter(template => 
        template.name.toLowerCase().includes(lowerKeyword) ||
        template.description.toLowerCase().includes(lowerKeyword) ||
        template.prompt.toLowerCase().includes(lowerKeyword)
      )
    }
  },
  actions: {
    addTemplate(template) {
      const newTemplate = {
        id: Date.now().toString(),
        userCreated: true,
        ...template
      }
      this.templates.push(newTemplate)
      return newTemplate
    },
    updateTemplate(id, template) {
      const index = this.templates.findIndex(t => t.id === id)
      if (index !== -1) {
        this.templates[index] = { ...this.templates[index], ...template }
        return this.templates[index]
      }
      return null
    },
    deleteTemplate(id) {
      const index = this.templates.findIndex(t => t.id === id)
      if (index !== -1) {
        this.templates.splice(index, 1)
        return true
      }
      return false
    }
  }
})
