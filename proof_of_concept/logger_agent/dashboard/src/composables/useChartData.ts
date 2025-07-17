import { ref, computed } from 'vue';
import type { HookEvent, ChartDataPoint, TimeRange } from '../types';

export function useChartData() {
  const timeRange = ref<TimeRange>('1m');
  const dataPoints = ref<ChartDataPoint[]>([]);
  
  // Store all events for re-aggregation when time range changes
  const allEvents = ref<HookEvent[]>([]);
  
  // Debounce for high-frequency events
  let eventBuffer: HookEvent[] = [];
  let debounceTimer: number | null = null;
  const DEBOUNCE_DELAY = 50; // 50ms debounce
  
  const timeRangeConfig = {
    '1m': {
      duration: 60 * 1000, // 1 minute in ms
      bucketSize: 1000, // 1 second buckets
      maxPoints: 60
    },
    '3m': {
      duration: 3 * 60 * 1000, // 3 minutes in ms
      bucketSize: 3000, // 3 second buckets
      maxPoints: 60
    },
    '5m': {
      duration: 5 * 60 * 1000, // 5 minutes in ms
      bucketSize: 5000, // 5 second buckets
      maxPoints: 60
    }
  };
  
  const currentConfig = computed(() => timeRangeConfig[timeRange.value]);
  
  const getBucketTimestamp = (timestamp: number): number => {
    const config = currentConfig.value;
    return Math.floor(timestamp / config.bucketSize) * config.bucketSize;
  };
  
  const processEventBuffer = () => {
    const eventsToProcess = [...eventBuffer];
    eventBuffer = [];
    
    // Add events to our complete list
    allEvents.value.push(...eventsToProcess);
    
    eventsToProcess.forEach(event => {
      if (!event.timestamp) return;
      
      const bucketTime = getBucketTimestamp(event.timestamp);
      
      // Find existing bucket or create new one
      let bucket = dataPoints.value.find(dp => dp.timestamp === bucketTime);
      if (bucket) {
        bucket.count++;
        // Track event types
        if (!bucket.eventTypes) {
          bucket.eventTypes = {};
        }
        bucket.eventTypes[event.hook_event_type] = (bucket.eventTypes[event.hook_event_type] || 0) + 1;
        // Track sessions
        if (!bucket.sessions) {
          bucket.sessions = {};
        }
        bucket.sessions[event.session_id] = (bucket.sessions[event.session_id] || 0) + 1;
      } else {
        dataPoints.value.push({
          timestamp: bucketTime,
          count: 1,
          eventTypes: { [event.hook_event_type]: 1 },
          sessions: { [event.session_id]: 1 }
        });
      }
    });
    
    // Clean old data once after processing all events
    cleanOldData();
    cleanOldEvents();
  };
  
  const addEvent = (event: HookEvent) => {
    eventBuffer.push(event);
    
    // Clear existing timer
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer);
    }
    
    // Set new timer
    debounceTimer = window.setTimeout(() => {
      processEventBuffer();
      debounceTimer = null;
    }, DEBOUNCE_DELAY);
  };
  
  const cleanOldData = () => {
    const now = Date.now();
    const cutoffTime = now - currentConfig.value.duration;
    
    dataPoints.value = dataPoints.value.filter(dp => dp.timestamp >= cutoffTime);
    
    // Ensure we don't exceed max points
    if (dataPoints.value.length > currentConfig.value.maxPoints) {
      dataPoints.value = dataPoints.value.slice(-currentConfig.value.maxPoints);
    }
  };
  
  const cleanOldEvents = () => {
    const now = Date.now();
    const cutoffTime = now - 5 * 60 * 1000; // Keep events for max 5 minutes
    
    allEvents.value = allEvents.value.filter(event => 
      event.timestamp && event.timestamp >= cutoffTime
    );
  };
  
  const getChartData = (): ChartDataPoint[] => {
    const now = Date.now();
    const config = currentConfig.value;
    const startTime = now - config.duration;
    
    // Create array of all time buckets in range
    const buckets: ChartDataPoint[] = [];
    for (let time = startTime; time <= now; time += config.bucketSize) {
      const bucketTime = getBucketTimestamp(time);
      const existingBucket = dataPoints.value.find(dp => dp.timestamp === bucketTime);
      buckets.push({
        timestamp: bucketTime,
        count: existingBucket?.count || 0,
        eventTypes: existingBucket?.eventTypes || {},
        sessions: existingBucket?.sessions || {}
      });
    }
    
    // Return only the last maxPoints buckets
    return buckets.slice(-config.maxPoints);
  };
  
  const setTimeRange = (range: TimeRange) => {
    timeRange.value = range;
    // Re-aggregate data for new bucket size
    reaggregateData();
  };
  
  const reaggregateData = () => {
    // Clear current data points
    dataPoints.value = [];
    
    // Re-process all events with new bucket size
    const now = Date.now();
    const cutoffTime = now - currentConfig.value.duration;
    
    // Filter events within the time range
    const relevantEvents = allEvents.value.filter(event => 
      event.timestamp && event.timestamp >= cutoffTime
    );
    
    // Re-aggregate all relevant events
    relevantEvents.forEach(event => {
      if (!event.timestamp) return;
      
      const bucketTime = getBucketTimestamp(event.timestamp);
      
      // Find existing bucket or create new one
      let bucket = dataPoints.value.find(dp => dp.timestamp === bucketTime);
      if (bucket) {
        bucket.count++;
        bucket.eventTypes[event.hook_event_type] = (bucket.eventTypes[event.hook_event_type] || 0) + 1;
        bucket.sessions[event.session_id] = (bucket.sessions[event.session_id] || 0) + 1;
      } else {
        dataPoints.value.push({
          timestamp: bucketTime,
          count: 1,
          eventTypes: { [event.hook_event_type]: 1 },
          sessions: { [event.session_id]: 1 }
        });
      }
    });
    
    // Clean up
    cleanOldData();
  };
  
  // Auto-clean old data every second
  const cleanupInterval = setInterval(() => {
    cleanOldData();
    cleanOldEvents();
  }, 1000);
  
  // Cleanup on unmount
  const cleanup = () => {
    clearInterval(cleanupInterval);
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer);
      processEventBuffer(); // Process any remaining events
    }
  };
  
  return {
    timeRange,
    dataPoints,
    addEvent,
    getChartData,
    setTimeRange,
    cleanup,
    currentConfig
  };
}