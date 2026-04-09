/* global Alpine */

// Alpine.js CDN を動的に読み込む
(function () {
  const s = document.createElement("script");
  s.defer = true;
  s.src = "https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js";
  document.head.appendChild(s);
})();

function watcher() {
  return {
    connected: false,
    filter: "all",
    services: [],
    gpu: { available: false, gpus: [] },
    unregistered: { count: 0, unregistered: [] },
    stats: {},   // { [service_id]: { cpu_percent, memory_percent } }
    pending: {}, // { [service_id]: boolean }
    _es: null,

    init() {
      this._connect();
    },

    _connect() {
      if (this._es) this._es.close();
      this._es = new EventSource("/api/stream");

      this._es.onopen = () => {
        this.connected = true;
      };

      this._es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.error) return;
          if (data.services && data.services.services) {
            this.services = data.services.services;
            // running サービスの stats を非同期取得
            this._fetchStats();
          }
          if (data.gpu) this.gpu = data.gpu;
          if (data.unregistered) this.unregistered = data.unregistered;
        } catch (_) {}
      };

      this._es.onerror = () => {
        this.connected = false;
        this._es.close();
        // 5秒後に再接続
        setTimeout(() => this._connect(), 5000);
      };
    },

    async _fetchStats() {
      const running = this.services.filter((s) => s.status === "running");
      for (const svc of running) {
        try {
          const resp = await fetch(`/api/services/${svc.id}/stats`);
          if (resp.ok) {
            const data = await resp.json();
            // Alpine のリアクティビティを維持するため直接代入
            this.stats = { ...this.stats, [svc.id]: data };
          }
        } catch (_) {}
      }
    },

    get filteredServices() {
      switch (this.filter) {
        case "running":
          return this.services.filter((s) => s.status === "running");
        case "stopped":
          return this.services.filter((s) => s.status !== "running");
        case "gpu":
          return this.services.filter((s) => s.gpu_required);
        case "on_demand":
          return this.services.filter((s) => s.on_demand);
        default:
          return this.services;
      }
    },

    async startService(id) {
      this.pending = { ...this.pending, [id]: true };
      try {
        await fetch(`/api/services/${id}/start`, { method: "POST" });
      } finally {
        this.pending = { ...this.pending, [id]: false };
      }
    },

    async stopService(id) {
      this.pending = { ...this.pending, [id]: true };
      try {
        await fetch(`/api/services/${id}/stop`, { method: "POST" });
      } finally {
        this.pending = { ...this.pending, [id]: false };
      }
    },

    statusLabel(status) {
      const map = { running: "● 稼働中", stopped: "○ 停止", exited: "○ 停止", paused: "⏸ 一時停止" };
      return map[status] || status;
    },

    formatSeconds(sec) {
      if (sec === null || sec === undefined) return "—";
      const h = Math.floor(sec / 3600);
      const m = Math.floor((sec % 3600) / 60);
      const s = sec % 60;
      if (h > 0) return `${h}時間${m}分`;
      if (m > 0) return `${m}分${s}秒`;
      return `${s}秒`;
    },
  };
}
