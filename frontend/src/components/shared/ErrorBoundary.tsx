import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
}

/**
 * P0-2 商业加固批：渲染异常兜底边界。
 *
 * 依据 freeze-diagnosis 实证：无边界时任何渲染异常 = React 整树卸载 =
 * 全交互静默死亡（root childElementCount = 0）。本组件保证：关键区域
 * 崩溃时降级为可见错误卡（绝不白屏），重试可复位，其余区域不受影响。
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, message: '' };

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : String(error),
    };
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    console.error('[ErrorBoundary] 渲染异常已拦截:', error, info.componentStack);
  }

  private handleRetry = () => {
    this.setState({ hasError: false, message: '' });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          data-testid="error-boundary"
          role="alert"
          className="glass-panel p-6 m-4 bg-cosmos-error/10 border border-cosmos-error/30 rounded-lg"
        >
          <h3 className="text-stardust-300 text-lg font-medium mb-2">
            这块区域出了点问题
          </h3>
          <p className="text-void-400 text-sm mb-4 break-all">
            {this.state.message || '未知错误'}
          </p>
          <button
            data-testid="error-boundary-retry"
            onClick={this.handleRetry}
            className="px-4 py-2 rounded-lg bg-stardust-400 text-space-950 hover:bg-stardust-300 text-sm font-medium transition-colors"
          >
            重试
          </button>
          <p className="text-void-500 text-xs mt-3">可点击重试，或先继续其他操作。</p>
        </div>
      );
    }
    return this.props.children;
  }
}
