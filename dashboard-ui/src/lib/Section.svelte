<script>
  // Collapsible section — compact header, expands inline. No redirects.
  // Progressive disclosure (design-lab / ui-ux-pro-max).
  let { title, subtitle = '', defaultOpen = false, badge = '', accent = 'var(--accent)', children } = $props();

  let open = $state(defaultOpen);
</script>

<section class="card" style:--accent={accent}>
  <button class="header" onclick={() => (open = !open)} aria-expanded={open}>
    <span class="h-text">
      <span class="h-title">{title}</span>
      {#if subtitle}<span class="h-sub">{subtitle}</span>{/if}
    </span>
    <span class="h-right">
      {#if badge}<span class="badge">{badge}</span>{/if}
      <svg class="chev" class:open viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </span>
  </button>

  {#if open}
    <div class="content">
      {@render children?.()}
    </div>
  {/if}
</section>

<style>
  .card {
    background: var(--surface-1);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-1);
    margin-bottom: var(--s-4);
    overflow: hidden;
  }
  .header {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-3);
    padding: var(--s-4);
    background: none;
    border: none;
    color: var(--text);
    cursor: pointer;
    font: inherit;
    text-align: left;
    min-height: 44px;
    transition: background 0.2s cubic-bezier(0.2, 0, 0, 1);
  }
  .header:hover { background: var(--surface-2); }
  .header:active { transform: scale(0.99); }

  .h-text { display: flex; flex-direction: column; min-width: 0; }
  .h-title { font-size: 1rem; font-weight: 600; letter-spacing: -0.01em; }
  .h-sub { font-size: 0.78rem; color: var(--text-dim); margin-top: 2px; }

  .h-right { display: flex; align-items: center; gap: var(--s-3); flex-shrink: 0; }
  .badge {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px var(--s-2);
    border-radius: var(--r-pill);
    background: var(--surface-3);
    color: var(--text-dim);
  }
  .chev {
    color: var(--text-faint);
    transition: transform 0.3s cubic-bezier(0.2, 0, 0, 1);
  }
  .chev.open { transform: rotate(180deg); }

  .content {
    padding: 0 var(--s-4) var(--s-4);
    /* no nested card chrome — inner content uses surface tint, not borders */
    animation: reveal 0.22s cubic-bezier(0.2, 0, 0, 1);
  }
  @keyframes reveal {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
