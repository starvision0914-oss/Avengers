import { useEffect, useState } from 'react';
import { getProjects, createProject, deleteProject } from '../../api/todos';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, FolderOpen } from 'lucide-react';
import toast from 'react-hot-toast';
import type { TodoProject } from '../../types';

export default function ProjectListPage() {
  const [projects, setProjects] = useState<TodoProject[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', color: '#3B82F6' });
  const navigate = useNavigate();

  const load = () => getProjects().then(d => setProjects(Array.isArray(d) ? d : d.results || []));
  useEffect(() => { load(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createProject(form);
    toast.success('프로젝트 생성 완료');
    setShowForm(false);
    setForm({ name: '', description: '', color: '#3B82F6' });
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">할 일 관리</h1>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-1 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm">
          <Plus size={16} /> 프로젝트 추가
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map(p => (
          <div key={p.id} className="bg-white rounded-lg shadow p-5 hover:shadow-md transition-shadow cursor-pointer" onClick={() => navigate(`/todos/${p.id}`)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: p.color }} />
                <h3 className="font-semibold">{p.name}</h3>
              </div>
              <button onClick={(e) => { e.stopPropagation(); deleteProject(p.id).then(() => { toast.success('삭제됨'); load(); }); }} className="text-gray-400 hover:text-red-600">
                <Trash2 size={16} />
              </button>
            </div>
            {p.description && <p className="text-sm text-gray-500 mt-2">{p.description}</p>}
            <p className="text-xs text-gray-400 mt-3">태스크 {p.task_count || 0}개</p>
          </div>
        ))}
        {projects.length === 0 && (
          <div className="col-span-3 text-center py-12 text-gray-400">
            <FolderOpen size={48} className="mx-auto mb-3" />
            <p>프로젝트가 없습니다. 새 프로젝트를 만들어보세요.</p>
          </div>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleSubmit} className="bg-white rounded-lg p-6 w-[400px]">
            <h2 className="text-lg font-bold mb-4">새 프로젝트</h2>
            <div className="space-y-3">
              <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="프로젝트명" className="w-full border rounded px-3 py-2" required />
              <textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})} placeholder="설명" className="w-full border rounded px-3 py-2" rows={3} />
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-500">색상:</label>
                <input type="color" value={form.color} onChange={e => setForm({...form, color: e.target.value})} className="w-8 h-8 rounded cursor-pointer" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">생성</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
