import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { EChartsOption } from 'echarts';
import { NgxEchartsModule } from 'ngx-echarts';
import { LightboxComponent } from '../../../../shared/components/lightbox/lightbox.component';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService, SentinelInvestigationGraph, SentinelGraphNode } from '../sentinel-api.service';

@Component({
  selector: 'app-sentinel-graph-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxEchartsModule, LightboxComponent],
  template: `
    <div class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h5 class="text-base font-bold text-slate-100 mb-0.5">
            Security Investigation Graph
          </h5>
          <p class="text-xs text-slate-400 mb-0">
            ความเชื่อมโยงระหว่าง Zone ↔ Camera ↔ Identity ↔ Incident (Company-scoped PostgreSQL)
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <select
            class="form-control !w-auto !py-1.5 !px-3 text-xs"
            [(ngModel)]="days"
            (ngModelChange)="loadGraph()"
            aria-label="Time window"
          >
            <option [ngValue]="1">24 ชั่วโมงล่าสุด</option>
            <option [ngValue]="7">7 วันล่าสุด</option>
            <option [ngValue]="30">30 วันล่าสุด</option>
          </select>
          <button
            type="button"
            class="ti-btn !rounded-full !px-3.5 !py-1.5 text-xs bg-cyan-500/20 text-cyan-200 border border-cyan-500/30"
            (click)="loadGraph()"
            [disabled]="loading()"
          >
            <i class="ri-refresh-line" [class.animate-spin]="loading()"></i>
            <span>{{ loading() ? 'กำลังโหลด...' : 'รีเฟรชกราฟ' }}</span>
          </button>
        </div>
      </div>

      @if (stats()) {
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="card-surface p-3 rounded-xl border border-cyan-500/20">
            <div class="text-[11px] text-slate-400">Zones</div>
            <div class="text-lg font-bold text-cyan-300">{{ stats()!.zones }}</div>
          </div>
          <div class="card-surface p-3 rounded-xl border border-sky-500/20">
            <div class="text-[11px] text-slate-400">Cameras</div>
            <div class="text-lg font-bold text-sky-300">{{ stats()!.cameras }}</div>
          </div>
          <div class="card-surface p-3 rounded-xl border border-violet-500/20">
            <div class="text-[11px] text-slate-400">Identities</div>
            <div class="text-lg font-bold text-violet-300">{{ stats()!.identities }}</div>
          </div>
          <div class="card-surface p-3 rounded-xl border border-rose-500/20">
            <div class="text-[11px] text-slate-400">Incidents ({{ days }}d)</div>
            <div class="text-lg font-bold text-rose-300">{{ stats()!.incidents }}</div>
          </div>
        </div>
      }

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div class="lg:col-span-9 card-surface rounded-2xl border border-white/10 p-3 min-h-[460px] relative">
          @if (chartOptions()) {
            <div
              echarts
              [options]="chartOptions()!"
              (chartClick)="onNodeClick($event)"
              class="w-full h-[440px]"
            ></div>
          } @else if (!loading()) {
            <div class="h-[440px] flex items-center justify-center text-sm text-slate-400">
              ยังไม่มีข้อมูลความเชื่อมโยงในองค์กรนี้
            </div>
          }
        </div>

        <div class="lg:col-span-3 card-surface rounded-2xl border border-white/10 p-4 space-y-3">
          <div class="text-xs font-bold uppercase tracking-wider text-cyan-300">
            Node Inspector
          </div>
          @if (selectedNode(); as node) {
            <div class="space-y-2 text-xs">
              <div class="text-sm font-bold text-slate-100 break-words">{{ node.name }}</div>
              <div class="inline-flex px-2 py-0.5 rounded-full bg-white/10 text-slate-200 text-[11px]">
                {{ node.meta['kind'] }}
              </div>
              @if (node.meta['severity']) {
                <div class="text-slate-300">Severity: <strong class="text-rose-300">{{ node.meta['severity'] }}</strong></div>
              }
              @if (node.meta['status']) {
                <div class="text-slate-300">Status: {{ node.meta['status'] }}</div>
              }
              @if (node.meta['stationMode']) {
                <div class="text-slate-300">Mode: {{ node.meta['stationMode'] }}</div>
              }
              @if (node.meta['occurredAt']) {
                <div class="text-slate-400">{{ node.meta['occurredAt'] }}</div>
              }
              @if (node.meta['snapshotUrl']) {
                <button
                  type="button"
                  class="ti-btn w-full !rounded-xl !py-2 bg-cyan-500/20 text-cyan-200 border border-cyan-500/30 text-xs mt-2"
                  (click)="lightboxUrl.set(String(node.meta['snapshotUrl']))"
                >
                  <i class="ri-image-line"></i>
                  <span>ดูภาพหลักฐาน (Lightbox)</span>
                </button>
              }
            </div>
          } @else {
            <p class="text-xs text-slate-400 leading-relaxed">
              คลิกที่ Node ในกราฟเพื่อดูรายละเอียด Zone, กล้อง, บุคคลเฝ้าระวัง หรือ Incident พร้อมเปิดดูภาพหลักฐาน
            </p>
          }

          <div class="pt-3 mt-3 border-t border-white/10 space-y-2">
            <div class="text-xs font-bold uppercase tracking-wider text-teal-300 flex items-center gap-1.5">
              <i class="ri-sparkling-2-line"></i>
              <span>Sentinel AI Copilot</span>
            </div>
            <div class="flex gap-1.5">
              <input
                type="text"
                class="form-control !py-1.5 !px-2.5 text-xs flex-1"
                [(ngModel)]="copilotPrompt"
                (keyup.enter)="askCopilot()"
                placeholder="ถามสรุปเหตุการณ์วันนี้..."
              />
              <button
                type="button"
                class="ti-btn !px-3 !py-1.5 text-xs bg-teal-500/20 text-teal-200 border border-teal-500/30 rounded-lg"
                [disabled]="copilotLoading() || !copilotPrompt.trim()"
                (click)="askCopilot()"
              >
                <i class="ri-send-plane-2-line" [class.animate-pulse]="copilotLoading()"></i>
              </button>
            </div>
            @if (copilotReply()) {
              <div class="p-2.5 rounded-xl bg-slate-900/80 border border-teal-500/20 text-xs text-slate-200 whitespace-pre-line leading-relaxed max-h-48 overflow-y-auto">
                {{ copilotReply() }}
              </div>
            }
          </div>
        </div>
      </div>
    </div>

    @if (lightboxUrl(); as url) {
      <app-lightbox
        [url]="url"
        [alt]="selectedNode()?.name || 'Incident snapshot'"
        [caption]="selectedNode()?.name"
        (closed)="lightboxUrl.set(null)"
      ></app-lightbox>
    }
  `,
})
export class SentinelGraphPanelComponent implements OnInit {
  private readonly api = inject(SentinelApiService);
  private readonly tokenService = inject(TokenService);

  days = 7;
  readonly loading = signal(false);
  readonly chartOptions = signal<EChartsOption | null>(null);
  readonly stats = signal<SentinelInvestigationGraph['stats'] | null>(null);
  readonly selectedNode = signal<SentinelGraphNode | null>(null);
  readonly lightboxUrl = signal<string | null>(null);
  copilotPrompt = '';
  readonly copilotLoading = signal(false);
  readonly copilotReply = signal<string | null>(null);
  protected readonly String = String;

  ngOnInit(): void {
    this.loadGraph();
  }

  loadGraph(): void {
    const companyId = this.tokenService.getSelectCompany()?.companyId;
    if (!companyId) return;

    this.loading.set(true);
    this.api.getInvestigationGraph(companyId, this.days).subscribe({
      next: (res) => {
        this.stats.set(res.stats);
        this.chartOptions.set({
          tooltip: {
            trigger: 'item',
            backgroundColor: '#070d14',
            borderColor: 'rgba(20, 184, 166, 0.4)',
            textStyle: { color: '#f1f5f9', fontSize: 12 },
          },
          legend: {
            data: res.categories.map((c) => c.name),
            textStyle: { color: '#cbd5e1', fontSize: 12 },
            top: 4,
          },
          color: ['#14b8a6', '#38bdf8', '#a78bfa', '#f43f5e'],
          series: [
            {
              type: 'graph',
              layout: 'force',
              roam: true,
              draggable: true,
              data: res.nodes.map((n) => ({
                ...n,
                label: { show: res.nodes.length <= 45, color: '#e2e8f0', fontSize: 11 },
              })),
              links: res.links.map((l) => ({
                ...l,
                lineStyle: { color: 'rgba(148, 163, 184, 0.35)', width: 1.4, curveness: 0.12 },
              })),
              categories: res.categories,
              force: {
                repulsion: 220,
                edgeLength: [60, 140],
                gravity: 0.08,
              },
              emphasis: {
                focus: 'adjacency',
                lineStyle: { width: 2.5 },
              },
            },
          ],
        });
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  onNodeClick(event: unknown): void {
    const ev = event as { dataType?: string; data?: SentinelGraphNode };
    if (ev?.dataType === 'node' && ev.data) {
      this.selectedNode.set(ev.data);
    }
  }

  askCopilot(): void {
    const companyId = this.tokenService.getSelectCompany()?.companyId;
    const msg = this.copilotPrompt.trim();
    if (!companyId || !msg || this.copilotLoading()) return;
    this.copilotLoading.set(true);
    this.api.askAssistant(companyId, msg).subscribe({
      next: (res) => {
        this.copilotReply.set(res.reply || '');
        this.copilotLoading.set(false);
      },
      error: () => {
        this.copilotReply.set('ไม่สามารถเชื่อมต่อ AI Copilot ได้ในขณะนี้');
        this.copilotLoading.set(false);
      },
    });
  }
}
