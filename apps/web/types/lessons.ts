export interface LessonParagraph {
  text: string;
  source_ids: number[];
}

export interface LessonSection {
  heading: string;
  paragraphs: LessonParagraph[];
  equations: string[];
  key_points: string[];
}

export interface LessonContent {
  intuition: string;
  sections: LessonSection[];
  paragraphs: LessonParagraph[]; // legacy flat lessons
  examples: string[];
  common_mistakes: string[];
  equations: string[];
}

export interface LessonSourceContext {
  index: number;
  source_id: string;
  title: string;
  publisher: string | null;
  year: number | null;
  authors: string[];
  url: string | null;
  excerpt: string;
  from_snippet: boolean;
}

export interface Lesson {
  concept_id: string;
  title: string;
  content: LessonContent;
  grounding: "GROUNDED" | "MIXED" | "GENERATED";
  sources: LessonSourceContext[];
  generated_at: string | null;
  cached: boolean;
}
