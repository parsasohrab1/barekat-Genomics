export interface Patient {
  id: string;
  external_id: string;
  age: number | null;
  gender: string | null;
  ehr_patient_id: string | null;
  created_at: string;
}

export interface PatientCreate {
  external_id: string;
  name?: string;
  age?: number;
  gender?: string;
  clinical_notes?: string;
  ehr_patient_id?: string;
}

export interface Sample {
  id: string;
  patient_id: string;
  sample_id: string;
  file_type: string;
  status: string;
  genome_build: string;
  created_at: string;
  patient_external_id?: string;
}

export interface PipelineJob {
  id: string;
  sample_id: string;
  paired_sample_id?: string | null;
  module?: string;
  stage: string;
  status: string;
  qc_metrics: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  sample_label?: string;
  progress?: number;
}

export interface GenomicsModule {
  id: string;
  name_fa: string;
  name_en: string;
  description_fa: string;
  category: string;
  gene_count: number;
  requires_paired_sample: boolean;
  cpic_guideline: boolean;
}

export interface PlainSummary {
  report_id?: string;
  plain_summary: string[];
  plain_summary_text: string;
  disclaimer: string;
  decision_support_only: boolean;
}

export interface VariantAskResult {
  answer_fa: string;
  blocked: boolean;
  disclaimer: string;
  decision_support_only: boolean;
  sources: string[];
  context_chunks: string[];
}

export interface Report {
  id: string;
  patient_id: string;
  report_type: string;
  status: string;
  summary: string | null;
  drug_recommendations: Record<string, DrugRecommendation> | null;
  clinical_content: ClinicalReportContent | null;
  variant_summary: Record<string, number> | null;
  created_at: string;
  finalized_at: string | null;
  approved_at?: string | null;
}

export interface DrugRecommendation {
  gene: string;
  significance: string;
  recommendation: string;
  confidence: number;
  drug_fa?: string;
  cpic_level?: string;
  cpic_level_label?: string;
  cpic_guideline?: string;
  action_fa?: string;
}

export interface ClinicalDrugRecommendation extends DrugRecommendation {
  drug: string;
}

export interface FeatureContribution {
  feature: string;
  contribution?: number;
  importance?: number;
}

export interface HighPriorityVariant {
  gene: string | null;
  rs_id: string | null;
  chromosome: string;
  position: number;
  ref_allele: string;
  alt_allele: string;
  clinical_significance: string;
  priority_score: number;
  interpretation: string | null;
  pharmacogenomic_effect?: string | null;
  ml_score?: number | null;
  ml_confidence?: number | null;
  rank?: number | null;
  model_version?: string | null;
  explain_method?: string | null;
  feature_contributions?: FeatureContribution[];
  guideline_drugs?: string[];
  knowledge_sources?: string[];
}

export interface BiomarkerMarker {
  rank?: number | null;
  gene?: string | null;
  rs_id?: string | null;
  clinical_significance?: string | null;
  priority_score?: number | null;
  ml_score?: number | null;
  pharmacogenomic_effect?: string | null;
  guideline_drugs?: string[];
  knowledge_sources?: string[];
  top_features?: FeatureContribution[];
  explain_method?: string | null;
  high_priority?: boolean;
}

export interface BiomarkerPanel {
  total_variants: number;
  high_priority_count: number;
  ranked_markers: BiomarkerMarker[];
}

export interface DrugInteraction {
  drugs: string[];
  drugs_fa?: string[];
  severity: string;
  severity_label?: string;
  warning_fa: string;
  recommendation_fa: string;
}

export interface ClinicalReportContent {
  schema_version?: string;
  executive_summary: string[];
  high_priority_variants: HighPriorityVariant[];
  biomarker_panel?: BiomarkerPanel | null;
  drug_recommendations: ClinicalDrugRecommendation[];
  drug_interactions: DrugInteraction[];
  digital_signature?: { signature: string; signed_at?: string; approver_id?: string } | null;
}

export interface ReviewQueueItem extends Report {
  pending_variant_count: number;
}

export interface PendingVariantItem {
  annotation_id: string;
  variant: {
    id: string;
    chromosome: string;
    position: number;
    ref_allele: string;
    alt_allele: string;
    variant_type: string;
    quality_score: number | null;
    rs_id: string | null;
  };
  gene: string | null;
  ml_score: number | null;
  ml_confidence: number | null;
  clinical_significance: string | null;
  interpretation: string | null;
  review_status: string | null;
  pharmacogenomic_effect: string | null;
}

export interface VariantAnnotation {
  gene: string | null;
  consequence: string | null;
  clinical_significance: string | null;
  pharmacogenomic_effect: string | null;
  priority_score: number | null;
  ml_confidence: number | null;
  interpretation: string | null;
}

export interface Variant {
  id: string;
  chromosome: string;
  position: number;
  ref_allele: string;
  alt_allele: string;
  variant_type: string;
  quality_score: number | null;
  rs_id: string | null;
  annotations: VariantAnnotation[];
  patient_external_id?: string;
  drug?: string | null;
}

export interface DashboardStats {
  total_patients: number;
  total_samples: number;
  active_pipelines: number;
  completed_reports: number;
  variants_detected: number;
  drug_recommendations: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface PlatformSettings {
  app_name: string;
  app_env: string;
  auth_enabled: boolean;
  audit_log_enabled: boolean;
  phi_retention_days: number;
  genome_build: string;
  pipeline_mode: string;
  pipeline_backend: string;
  ai_assist_enabled: boolean;
  metrics_enabled: boolean;
  ml_ab_test_enabled: boolean;
  variant_classifier_model: string;
  ehr_fhir_organization_id: string;
  ehr_hl7_sending_facility: string;
  clinical_report_schema_version: string;
}

export interface ApiError {
  detail: string;
}
