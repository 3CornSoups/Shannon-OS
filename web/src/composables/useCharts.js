import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

/**
 * Chart Manager - Unified chart lifecycle management
 * Handles initialization, updates, disposal, and resize operations
 */
export class ChartManager {
  constructor() {
    this.charts = {}
    this.isDisposed = false
    this.logger = this._createLogger()
  }

  _createLogger() {
    return {
      info: (msg, data) => console.log('[ChartManager]', msg, data || ''),
      warn: (msg, data) => console.warn('[ChartManager]', msg, data || ''),
      error: (msg, error) => console.error('[ChartManager]', msg, error || '')
    }
  }

  /**
   * Safely initialize a chart with container validation
   */
  async initChart(chartName, containerRef, baseOptions = {}) {
    if (this.isDisposed) {
      this.logger.warn(`Cannot init chart ${chartName}: manager disposed`)
      return null
    }

    if (!containerRef) {
      this.logger.warn(`Chart ${chartName} container ref is null`)
      return null
    }

    try {
      // Wait for container to be visible and have dimensions
      let attempts = 0
      while (attempts < 10) {
        const rect = containerRef.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) break
        await new Promise(resolve => setTimeout(resolve, 50))
        attempts++
      }

      const rect = containerRef.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) {
        this.logger.error(`Chart ${chartName} container has zero dimensions after retries`)
        return null
      }

      // Dispose existing chart if any
      if (this.charts[chartName]) {
        this.charts[chartName].dispose()
        delete this.charts[chartName]
      }

      // Initialize new chart
      const chart = echarts.init(containerRef)
      
      // Set base options
      chart.setOption({
        ...this._getDefaultTheme(),
        ...baseOptions
      }, { notMerge: true })

      this.charts[chartName] = chart
      this.logger.info(`Chart ${chartName} initialized`)
      return chart
    } catch (error) {
      this.logger.error(`Failed to initialize chart ${chartName}`, error)
      return null
    }
  }

  /**
   * Update chart with new options
   */
  updateChart(chartName, options, merge = true) {
    const chart = this.charts[chartName]
    if (!chart) {
      this.logger.warn(`Chart ${chartName} not found for update`)
      return false
    }

    if (this.isDisposed) {
      this.logger.warn(`Cannot update chart ${chartName}: manager disposed`)
      return false
    }

    try {
      chart.setOption(options, { notMerge: !merge })
      return true
    } catch (error) {
      this.logger.error(`Failed to update chart ${chartName}`, error)
      return false
    }
  }

  /**
   * Resize all charts
   */
  resizeAll() {
    Object.entries(this.charts).forEach(([name, chart]) => {
      try {
        chart.resize()
      } catch (error) {
        this.logger.error(`Failed to resize chart ${name}`, error)
      }
    })
  }

  /**
   * Resize single chart
   */
  resize(chartName) {
    const chart = this.charts[chartName]
    if (chart) {
      try {
        chart.resize()
      } catch (error) {
        this.logger.error(`Failed to resize chart ${chartName}`, error)
      }
    }
  }

  /**
   * Dispose all charts and cleanup
   */
  dispose() {
    this.isDisposed = true
    Object.entries(this.charts).forEach(([name, chart]) => {
      try {
        chart.dispose()
        this.logger.info(`Chart ${name} disposed`)
      } catch (error) {
        this.logger.error(`Failed to dispose chart ${name}`, error)
      }
    })
    this.charts = {}
  }

  /**
   * Get chart instance
   */
  getChart(chartName) {
    return this.charts[chartName] || null
  }

  /**
   * Get default theme options
   */
  _getDefaultTheme() {
    return {
      backgroundColor: 'transparent',
      animation: false,
      textStyle: {
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
      }
    }
  }
}

/**
 * Composable for chart management in Vue components
 */
export function useCharts() {
  const chartManager = new ChartManager()
  const chartRefs = ref({})
  const chartsReady = ref({})

  /**
   * Register chart reference
   */
  const registerChartRef = (chartName, element) => {
    if (element) {
      chartRefs.value[chartName] = element
    }
  }

  /**
   * Initialize all charts
   */
  const initCharts = async (chartConfigs) => {
    await nextTick()
    
    // Small delay to ensure DOM is fully rendered
    await new Promise(resolve => setTimeout(resolve, 50))

    for (const [name, config] of Object.entries(chartConfigs)) {
      const container = chartRefs.value[name]
      if (!container) {
        chartManager.logger.warn(`Chart container ${name} not found`)
        continue
      }

      const chart = await chartManager.initChart(name, container, config.options)
      if (chart) {
        chartsReady.value[name] = true
      }
    }
  }

  /**
   * Update all charts
   */
  const updateCharts = (updates) => {
    for (const [name, options] of Object.entries(updates)) {
      chartManager.updateChart(name, options)
    }
  }

  /**
   * Handle window resize with debounce
   */
  let resizeTimer = null
  const handleResize = () => {
    if (resizeTimer) clearTimeout(resizeTimer)
    resizeTimer = setTimeout(() => {
      chartManager.resizeAll()
    }, 200)
  }

  // Setup resize listener
  onMounted(() => {
    window.addEventListener('resize', handleResize)
  })

  // Cleanup on unmount
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    if (resizeTimer) clearTimeout(resizeTimer)
    chartManager.dispose()
  })

  return {
    chartManager,
    chartRefs,
    chartsReady,
    registerChartRef,
    initCharts,
    updateCharts,
    handleResize
  }
}

/**
 * Chart option generators
 */
export const ChartOptions = {
  /**
   * CPU core usage bar chart
   */
  cpuCoreUsage(cores, overallUsage) {
    const coreNames = cores.map((_, i) => `Core ${i}`)
    return {
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
      xAxis: {
        type: 'category',
        data: coreNames.length > 0 ? coreNames : ['CPU'],
        axisLine: { lineStyle: { color: '#E5E7EB' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: { formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#F3F4F6' } }
      },
      series: [{
        data: cores.length > 0 ? cores : [overallUsage],
        type: 'bar',
        barWidth: '50%',
        itemStyle: {
          color: '#4F6EF7',
          borderRadius: [4, 4, 0, 0]
        }
      }]
    }
  },

  /**
   * Memory usage pie chart
   */
  memoryUsage(usedPercent) {
    return {
      animation: false,
      tooltip: { trigger: 'item' },
      series: [{
        name: '内存',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{d}%'
        },
        labelLine: { show: true },
        data: [
          { value: usedPercent, name: '已使用', itemStyle: { color: '#4F6EF7' } },
          { value: 100 - usedPercent, name: '可用', itemStyle: { color: '#E5E7EB' } }
        ]
      }]
    }
  },

  /**
   * Disk usage bar chart
   */
  diskUsage(partitions) {
    const diskData = partitions.map(p => ({
      name: p.mount,
      value: p.usage_percent,
      itemStyle: {
        color: p.usage_percent > 90 ? '#EF4444' : p.usage_percent > 70 ? '#F59E0B' : '#22C55E',
        borderRadius: [4, 4, 0, 0]
      }
    }))

    return {
      animation: false,
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
      xAxis: {
        type: 'category',
        data: diskData.map(d => d.name),
        axisLine: { lineStyle: { color: '#E5E7EB' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: { formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#F3F4F6' } }
      },
      series: [{
        data: diskData,
        type: 'bar',
        barWidth: '50%'
      }]
    }
  },

  /**
   * Network traffic bar chart
   */
  networkTraffic(interfaces) {
    const ifaceNames = interfaces.map(i => i.name)
    const rxData = interfaces.map(i => i.rx_bytes)
    const txData = interfaces.map(i => i.tx_bytes)

    return {
      animation: false,
      tooltip: { trigger: 'axis' },
      legend: { data: ['接收', '发送'], bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '30px', top: '8%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ifaceNames,
        axisLine: { lineStyle: { color: '#E5E7EB' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#F3F4F6' } }
      },
      series: [
        { name: '接收', data: rxData, type: 'bar', itemStyle: { color: '#22C55E', borderRadius: [4, 4, 0, 0] } },
        { name: '发送', data: txData, type: 'bar', itemStyle: { color: '#4F6EF7', borderRadius: [4, 4, 0, 0] } }
      ]
    }
  },

  /**
   * History trend line chart
   */
  historyTrend(times, values, color, name, unit = '%') {
    return {
      animation: false,
      tooltip: {
        trigger: 'axis',
        formatter: `{b}<br/>${name}: {c}${unit}`
      },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
      xAxis: {
        type: 'category',
        data: times,
        boundaryGap: false,
        axisLabel: { fontSize: 10 },
        axisLine: { lineStyle: { color: '#E5E7EB' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: { formatter: `{value}${unit}` },
        splitLine: { lineStyle: { color: '#F3F4F6' } }
      },
      series: [{
        name: name,
        data: values,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2, color: color },
        itemStyle: { color: color },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: color + '26' },
            { offset: 1, color: color + '05' }
          ])
        }
      }]
    }
  }
}