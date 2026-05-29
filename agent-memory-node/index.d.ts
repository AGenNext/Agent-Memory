export interface MemoryInput {
  agentId: string
  content: string
  /** 'episodic' | 'identity' | 'knowledge' | 'context' | 'instruction' | 'uncertainty' */
  category: string
  sessionId?: string
  importance?: number
  confidence?: number
  keywords?: string[]
  tags?: string[]
  /** 'fact' | 'belief' | 'assumption' | 'hearsay' | 'inferred' */
  epistemicStatus?: string
}

export interface Memory {
  id?: string
  category: string
  content: string
  agentId: string
  confidence: number
  importance: number
  epistemicStatus: string
  superseded: boolean
  knownTime?: string
}

export interface RecallQuery {
  agentId: string
  queryText: string
  topK?: number
  categories?: string[]
  sessionId?: string
  minConfidence?: number
}

export interface RecallResult {
  memories: Memory[]
  tierUsed: number
  candidates: number
}

export interface RecallOutcome {
  /** 'found' | 'gap' */
  outcome: string
  memories?: Memory[]
  gapProbeId?: string
  suggestedPrompt?: string
  tiersTried?: number[]
}

export interface UpdateResult {
  superseded: Memory
  new: Memory
}

export interface ConflictTrace {
  agentResponse: string
  haltReasoning: boolean
  resolution: string
  interpretationVersion?: number
}

export interface WorkingMemory {
  layer: string
  content: string
  tokenCount?: number
}

export declare class AgentMemory {
  /** Open persistent memory at dataDir. */
  static open(dataDir: string): Promise<AgentMemory>

  /** Open ephemeral in-memory store. Data lost on drop. For testing. */
  static openMem(): Promise<AgentMemory>

  /** Store a new memory. */
  remember(input: MemoryInput): Promise<Memory>

  /** Retrieve memories using hybrid search (BM25 + vector + RRF). */
  recall(query: RecallQuery): Promise<RecallResult>

  /**
   * Recall with full escalation — tries all tiers before returning a gap.
   * If nothing found, returns a gap probe with a suggested prompt for the human.
   */
  recallOrGap(query: RecallQuery, humanInsistence?: string): Promise<RecallOutcome>

  /** Supersede a memory — old record preserved, new record created. */
  update(oldMemoryId: string, newContent: string, confidence?: number): Promise<UpdateResult>

  /** Soft-forget a memory. History remains queryable. */
  forget(memoryId: string): Promise<void>

  /** Reinforce memories — resets their Ebbinghaus decay. */
  reinforce(memoryIds: string[]): Promise<void>

  /**
   * Resolve a conflict.
   * @param conflictType 'misinterpretation' | 'agent_stands_firm' | 'factual_contradiction'
   */
  resolveConflict(
    agentId: string,
    sessionId: string | null,
    conflictType: string,
    humanStatement: string,
    priorMemoryId?: string,
    correctInterpretation?: string,
  ): Promise<ConflictTrace>

  /** Assembled working memory layers — inject into LLM system prompt. */
  context(agentId: string): Promise<WorkingMemory[]>

  /**
   * Run an analytics query.
   * @param query 'decay_tuning' | 'recall_health' | 'conflict_patterns' |
   *              'memory_growth' | 'reinforcement' | 'session_patterns' |
   *              'summary' | 'available'
   */
  analytics(agentId: string, query: string, windowDays?: number): Promise<object>

  /** Clear active episode when a session ends. */
  endSession(agentId: string): Promise<void>
}
