import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import md from '../../content/ai100_reference.md?raw';

export default function RoadmapPage() {
  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto', fontSize: 15, lineHeight: 1.7, color: '#1f2937' }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ ...p }) => <h1 style={{ fontSize: 26, fontWeight: 800, margin: '8px 0 16px' }} {...p} />,
          h2: ({ ...p }) => <h2 style={{ fontSize: 20, fontWeight: 800, margin: '28px 0 10px', paddingBottom: 6, borderBottom: '2px solid #e5e7eb' }} {...p} />,
          h3: ({ ...p }) => <h3 style={{ fontSize: 16, fontWeight: 700, margin: '18px 0 8px', color: '#374151' }} {...p} />,
          p: ({ ...p }) => <p style={{ margin: '8px 0' }} {...p} />,
          ul: ({ ...p }) => <ul style={{ margin: '6px 0', paddingLeft: 22 }} {...p} />,
          li: ({ ...p }) => <li style={{ margin: '3px 0' }} {...p} />,
          hr: () => <hr style={{ border: 0, borderTop: '1px solid #e5e7eb', margin: '24px 0' }} />,
          a: ({ ...p }) => <a style={{ color: '#2563eb' }} {...p} />,
          blockquote: ({ ...p }) => <blockquote style={{ borderLeft: '4px solid #d1d5db', margin: '10px 0', padding: '4px 14px', color: '#6b7280', background: '#f9fafb' }} {...p} />,
          code: ({ ...p }) => <code style={{ background: '#f3f4f6', padding: '1px 6px', borderRadius: 4, fontSize: 13, color: '#b45309', fontFamily: 'monospace' }} {...p} />,
          pre: ({ ...p }) => <pre style={{ background: '#1f2937', color: '#e5e7eb', padding: 14, borderRadius: 8, overflowX: 'auto', fontSize: 13 }} {...p} />,
          table: ({ ...p }) => <div style={{ overflowX: 'auto' }}><table style={{ borderCollapse: 'collapse', width: '100%', margin: '10px 0', fontSize: 14 }} {...p} /></div>,
          th: ({ ...p }) => <th style={{ border: '1px solid #e5e7eb', padding: '6px 10px', background: '#f3f4f6', textAlign: 'left', fontWeight: 700 }} {...p} />,
          td: ({ ...p }) => <td style={{ border: '1px solid #e5e7eb', padding: '6px 10px' }} {...p} />,
        }}
      >
        {md}
      </ReactMarkdown>
    </div>
  );
}
