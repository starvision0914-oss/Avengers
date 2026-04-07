import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTasks, createTask, updateTask, moveTask, deleteTask, getMembers } from '../../api/todos';
import { DndContext, closestCenter, DragEndEvent } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Plus, ArrowLeft, Trash2, GripVertical } from 'lucide-react';
import toast from 'react-hot-toast';
import type { TodoTask, TodoMember } from '../../types';

const COLUMNS = [
  { key: 'waiting', label: '대기', color: 'bg-gray-100' },
  { key: 'in_progress', label: '진행중', color: 'bg-blue-50' },
  { key: 'review', label: '검토', color: 'bg-yellow-50' },
  { key: 'done', label: '완료', color: 'bg-green-50' },
  { key: 'hold', label: '보류', color: 'bg-red-50' },
];

const PRIORITY_COLORS: Record<string, string> = {
  low: 'border-l-gray-300',
  normal: 'border-l-blue-400',
  high: 'border-l-orange-400',
  urgent: 'border-l-red-500',
};

function TaskCard({ task, onDelete }: { task: TodoTask; onDelete: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: task.id });
  const style = { transform: CSS.Transform.toString(transform), transition };

  return (
    <div ref={setNodeRef} style={style} className={`bg-white rounded-lg shadow-sm p-3 mb-2 border-l-4 ${PRIORITY_COLORS[task.priority] || 'border-l-gray-300'}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1 cursor-grab" {...attributes} {...listeners}>
          <p className="text-sm font-medium">{task.title}</p>
          {task.due_date && <p className="text-xs text-gray-400 mt-1">{task.due_date}</p>}
          {task.assigned_to_name && <p className="text-xs text-blue-500 mt-1">{task.assigned_to_name}</p>}
        </div>
        <button onClick={onDelete} className="text-gray-300 hover:text-red-500 ml-2"><Trash2 size={14} /></button>
      </div>
    </div>
  );
}

export default function KanbanBoard() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TodoTask[]>([]);
  const [members, setMembers] = useState<TodoMember[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [newStatus, setNewStatus] = useState('waiting');
  const [form, setForm] = useState({ title: '', content: '', priority: 'normal', assigned_to: '', due_date: '' });

  const load = () => {
    getTasks({ project: projectId! }).then(d => setTasks(Array.isArray(d) ? d : d.results || []));
    getMembers().then(d => setMembers(Array.isArray(d) ? d : d.results || []));
  };
  useEffect(() => { load(); }, [projectId]);

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const overId = String(over.id);
    const col = COLUMNS.find(c => c.key === overId);
    if (col) {
      await moveTask(Number(active.id), { status: col.key });
      load();
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    await createTask({ ...form, project: projectId, status: newStatus, assigned_to: form.assigned_to || null });
    toast.success('태스크 추가');
    setShowForm(false);
    setForm({ title: '', content: '', priority: 'normal', assigned_to: '', due_date: '' });
    load();
  };

  const handleDelete = async (id: number) => {
    await deleteTask(id);
    load();
  };

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/todos')} className="text-gray-500 hover:text-gray-700"><ArrowLeft size={20} /></button>
        <h1 className="text-2xl font-bold">칸반 보드</h1>
      </div>

      <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map(col => {
            const colTasks = tasks.filter(t => t.status === col.key);
            return (
              <div key={col.key} className={`${col.color} rounded-lg p-3 min-w-[260px] w-[260px] flex-shrink-0`}>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-sm">{col.label} <span className="text-gray-400">({colTasks.length})</span></h3>
                  <button onClick={() => { setNewStatus(col.key); setShowForm(true); }} className="text-gray-400 hover:text-blue-600"><Plus size={16} /></button>
                </div>
                <SortableContext items={colTasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
                  <div className="min-h-[200px]" id={col.key}>
                    {colTasks.map(task => (
                      <TaskCard key={task.id} task={task} onDelete={() => handleDelete(task.id)} />
                    ))}
                  </div>
                </SortableContext>
              </div>
            );
          })}
        </div>
      </DndContext>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleAdd} className="bg-white rounded-lg p-6 w-[400px]">
            <h2 className="text-lg font-bold mb-4">새 태스크</h2>
            <div className="space-y-3">
              <input value={form.title} onChange={e => setForm({...form, title: e.target.value})} placeholder="제목" className="w-full border rounded px-3 py-2" required />
              <textarea value={form.content} onChange={e => setForm({...form, content: e.target.value})} placeholder="내용" className="w-full border rounded px-3 py-2" rows={3} />
              <select value={form.priority} onChange={e => setForm({...form, priority: e.target.value})} className="w-full border rounded px-3 py-2">
                <option value="low">낮음</option>
                <option value="normal">보통</option>
                <option value="high">높음</option>
                <option value="urgent">긴급</option>
              </select>
              <select value={form.assigned_to} onChange={e => setForm({...form, assigned_to: e.target.value})} className="w-full border rounded px-3 py-2">
                <option value="">담당자 없음</option>
                {members.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <input type="date" value={form.due_date} onChange={e => setForm({...form, due_date: e.target.value})} className="w-full border rounded px-3 py-2" />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">추가</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
