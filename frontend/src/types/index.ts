export interface SellerAccount {
  id: number;
  seller_id: string;
  seller_name: string;
  platform: string;
  is_active: boolean;
  display_order: number;
  memo: string;
  created_at: string;
  updated_at: string;
}

export interface CPCDailyCost {
  id: number;
  seller: number;
  seller_name?: string;
  seller_id_display?: string;
  date: string;
  cpc_cost: number;
  ai_cost: number;
  total_cost: number;
  clicks: number;
  impressions: number;
  conversions: number;
  roas: number;
  created_at: string;
}

export interface CPCDeposit {
  id: number;
  seller: number;
  seller_name?: string;
  balance: number;
  deposited_amount: number;
  deposit_date: string;
  memo: string;
}

export interface CPCTransaction {
  id: number;
  seller: number;
  seller_name?: string;
  transaction_time: string;
  category: string;
  description: string;
  amount: number;
  product_code: string;
  product_name: string;
}

export interface SalesRecord {
  id: number;
  seller: number;
  seller_name?: string;
  order_date: string;
  order_number: string;
  product_name: string;
  product_code: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  commission: number;
  shipping_fee: number;
  net_profit: number;
  status: string;
}

export interface TodoMember {
  id: number;
  name: string;
  avatar_color: string;
  is_active: boolean;
}

export interface TodoProject {
  id: number;
  name: string;
  description: string;
  color: string;
  status: string;
  task_count?: number;
}

export interface TodoTask {
  id: number;
  project: number;
  title: string;
  content: string;
  status: string;
  priority: string;
  assigned_to: number | null;
  assigned_to_name?: string;
  due_date: string | null;
  display_order: number;
  comments?: TodoComment[];
  created_at: string;
  updated_at: string;
}

export interface TodoComment {
  id: number;
  task: number;
  member: number | null;
  member_name?: string;
  content: string;
  created_at: string;
}

export interface ChatRoom {
  id: number;
  name: string;
  room_type: string;
  members?: ChatMember[];
  last_message?: ChatMessage;
  created_at: string;
}

export interface ChatMember {
  id: number;
  room: number;
  name: string;
}

export interface ChatMessage {
  id: number;
  room: number;
  sender: string;
  content: string;
  message_type: string;
  file_url: string;
  created_at: string;
}

export interface EmailAccount {
  id: number;
  email_address: string;
  display_name: string;
  provider: string;
  imap_host: string;
  imap_port: number;
  smtp_host: string;
  smtp_port: number;
  smtp_use_tls: boolean;
  username: string;
  is_active: boolean;
  last_synced_at: string | null;
}

export interface EmailMsg {
  id: number;
  account: number;
  account_email?: string;
  folder: string;
  subject: string;
  from_addr: string;
  from_name: string;
  to_addrs: string[];
  cc_addrs: string[];
  date: string;
  snippet: string;
  body_text?: string;
  body_html?: string;
  has_attachment: boolean;
  is_read: boolean;
  is_starred: boolean;
}
