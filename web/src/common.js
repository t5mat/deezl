function promisify(f) {
  return (...args) => {
    return new Promise((resolve, reject) => {
      f.call(null, ...args, (err, res) => {
        if (err) {
          reject(err)
        } else {
          resolve(res)
        }
      })
    })
  }
}


import {format, parseISO, addSeconds} from 'date-fns'

export function formatDate(s) {
  return format(parseISO(s), 'yyyy-MM-dd')
}

export function formatSecondsDuration(seconds) {
  return format(addSeconds(new Date(0), seconds), 'm:ss')
}


import {zip as zip_} from 'fflate'

export const zip = promisify(zip_)


import {ref, onMounted, watchEffect} from 'vue'
import {useResizeObserver} from '@vueuse/core'
import {createPopper} from '@popperjs/core'

export function usePopper(options) {
  const trigger = ref(null)
  const container = ref(null)

  const instance = ref(null)

  onMounted(() => {
    watchEffect((onInvalidate) => {
      if (!trigger.value || !container.value) {
        return
      }

      const triggerElement = trigger.value.el ?? trigger.value
      const containerElement = container.value.el ?? container.value
      if (!(triggerElement instanceof HTMLElement) || !(containerElement instanceof HTMLElement)) {
        return
      }

      instance.value = createPopper(triggerElement, containerElement, options)
      onInvalidate(() => {
        instance.value.destroy()
      })
    })
  })

  useResizeObserver(container, () => {
    if (!instance.value) {
      return
    }
    instance.value.update()
  })

  return [trigger, container]
}
