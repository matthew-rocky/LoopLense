export type AnyRow = Record<string, unknown>;

export type Summary = {
  total_loops: number;
  total_edges: number;
  total_charities_entities: number;
  high_priority_loops: number;
  total_circular_flow: number | null;
  review_label_distribution: { review_label: string; count: number }[];
  top_high_priority_loops: AnyRow[];
  flow_column?: string;
};

export type LoopDetail = {
  loop: AnyRow;
  edges: AnyRow[];
  people: AnyRow[];
  score_explanation: AnyRow;
};

export type NetworkGraph = {
  loop_id: string;
  summary?: {
    participant_count?: number;
    circular_flow?: number;
    score?: number;
    label?: string;
    min_year?: number;
    max_year?: number;
    total_edges?: number;
    highest_transfer_edge?: number;
  };
  nodes: {
    id: string;
    label: string;
    bn?: string;
    legal_name?: string;
    account_name?: string;
    city?: string;
    province?: string;
    position_in_loop?: number | string | null;
    total_sent?: number;
    total_received?: number;
    outgoing_edges?: number;
    incoming_edges?: number;
    is_cycle_node?: boolean;
    type: string;
    metadata: AnyRow;
  }[];
  edges: {
    id?: string;
    source: string;
    target: string;
    source_name?: string;
    target_name?: string;
    amount?: number;
    edge_count?: number;
    min_year?: number;
    max_year?: number;
    years?: number[];
    is_cycle_edge?: boolean;
    is_inferred?: boolean;
    evidence_source?: string;
    metadata: AnyRow;
  }[];
  highlight_circular_path?: string[];
};

export type ChatResponse = {
  answer: string;
  intent: string;
  data: AnyRow[];
  evidence: AnyRow[];
  suggested_followups: string[];
  chart?: AnyRow;
  verification?: AnyRow;
  memo?: AnyRow;
  memo_verification?: AnyRow;
  method?: string;
};

export type MemoResponse = {
  memo: AnyRow;
  checks: AnyRow[];
  safe: boolean;
  disclaimer: string;
};
