import React, { FormEvent, useCallback, useMemo, useState } from 'react';
import { VoiceAssistantProvider } from '../contexts/VoiceAssistantContext';
import { VoiceAssistantPanel } from '../components/voice/VoiceAssistantPanel';
import type { JobPostingFormData } from '../types/voice-assistant';

const initialFormValues: Partial<JobPostingFormData> = {
  job_title: '',
  company_name: '',
  location: '',
  work_type: '',
  employment_type: '',
  salary_min: null,
  salary_max: null,
  skills_required: [],
  job_description: '',
};

export default function CreateJobPosting() {
  const [formValues, setFormValues] = useState<Partial<JobPostingFormData>>(initialFormValues);
  const [justUpdatedFields, setJustUpdatedFields] = useState<Set<string>>(new Set());

  const skillsRequiredText = useMemo(
    () => (formValues.skills_required ?? []).join(', '),
    [formValues.skills_required]
  );

  const handleVoiceFieldUpdate = useCallback(
    (field: keyof JobPostingFormData, value: any) => {
      // This callback fires for every individual field update during the conversation.
      // It merges the incoming field into the form's state.
      setFormValues((prev) => ({ ...prev, [field]: value }));

      // IMPORTANT: Add the field-updated CSS animation class to the DOM element
      // for this field so the recruiter sees a visual highlight.
      setJustUpdatedFields((prev) => new Set(prev).add(field as string));
      setTimeout(() => {
        setJustUpdatedFields((prev) => {
          const next = new Set(prev);
          next.delete(field as string);
          return next;
        });
      }, 2000);
    },
    [
      setFormValues,
      // Keep the form setter in deps to avoid stale closure bugs
      // if the state management implementation changes.
    ]
  );

  const handleVoiceSessionComplete = useCallback(
    (jobData: JobPostingFormData) => {
      // This callback fires once at the end of the session with a complete snapshot.
      // It merges ALL collected fields into the form at once.
      setFormValues((prev) => ({ ...prev, ...jobData }));
    },
    [setFormValues]
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    console.log('Submitting job posting:', formValues);
  };

  const fieldClass = (fieldName: string) =>
    `va-form-input ${justUpdatedFields.has(fieldName) ? 'va-field-updated' : ''}`;

  return (
    <VoiceAssistantProvider
      onFieldUpdate={handleVoiceFieldUpdate}
      onSessionComplete={handleVoiceSessionComplete}
    >
      <div
        className="create-job-posting-page"
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) 380px',
          gap: '20px',
          alignItems: 'start',
          padding: '20px',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <h1 style={{ marginTop: 0 }}>Create Job Posting</h1>
          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '14px' }}>
            <label>
              Job Title
              <input
                name="job_title"
                className={fieldClass('job_title')}
                value={formValues.job_title ?? ''}
                onChange={(event) =>
                  setFormValues((prev) => ({ ...prev, job_title: event.target.value }))
                }
              />
            </label>

            <label>
              Company Name
              <input
                name="company_name"
                className={fieldClass('company_name')}
                value={formValues.company_name ?? ''}
                onChange={(event) =>
                  setFormValues((prev) => ({ ...prev, company_name: event.target.value }))
                }
              />
            </label>

            <label>
              Location
              <input
                name="location"
                className={fieldClass('location')}
                value={formValues.location ?? ''}
                onChange={(event) =>
                  setFormValues((prev) => ({ ...prev, location: event.target.value }))
                }
              />
            </label>

            <label>
              Work Type
              <select
                name="work_type"
                className={fieldClass('work_type')}
                value={formValues.work_type ?? ''}
                onChange={(event) =>
                  setFormValues((prev) => ({ ...prev, work_type: event.target.value }))
                }
              >
                <option value="">Select work type</option>
                <option value="remote">Remote</option>
                <option value="onsite">Onsite</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </label>

            <label>
              Employment Type
              <select
                name="employment_type"
                className={fieldClass('employment_type')}
                value={formValues.employment_type ?? ''}
                onChange={(event) =>
                  setFormValues((prev) => ({ ...prev, employment_type: event.target.value }))
                }
              >
                <option value="">Select employment type</option>
                <option value="full-time">Full-time</option>
                <option value="part-time">Part-time</option>
                <option value="contract">Contract</option>
                <option value="internship">Internship</option>
              </select>
            </label>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <label>
                Salary Min
                <input
                  name="salary_min"
                  type="number"
                  className={fieldClass('salary_min')}
                  value={formValues.salary_min ?? ''}
                  onChange={(event) => {
                    const raw = event.target.value;
                    setFormValues((prev) => ({
                      ...prev,
                      salary_min: raw === '' ? null : Number(raw),
                    }));
                  }}
                />
              </label>

              <label>
                Salary Max
                <input
                  name="salary_max"
                  type="number"
                  className={fieldClass('salary_max')}
                  value={formValues.salary_max ?? ''}
                  onChange={(event) => {
                    const raw = event.target.value;
                    setFormValues((prev) => ({
                      ...prev,
                      salary_max: raw === '' ? null : Number(raw),
                    }));
                  }}
                />
              </label>
            </div>

            <label>
              Required Skills (comma-separated)
              <input
                name="skills_required"
                className={fieldClass('skills_required')}
                value={skillsRequiredText}
                onChange={(event) => {
                  const nextSkills = event.target.value
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean);
                  setFormValues((prev) => ({ ...prev, skills_required: nextSkills }));
                }}
              />
            </label>

            <label>
              Job Description
              <textarea
                name="job_description"
                className={fieldClass('job_description')}
                rows={5}
                value={formValues.job_description ?? ''}
                onChange={(event) =>
                  setFormValues((prev) => ({ ...prev, job_description: event.target.value }))
                }
              />
            </label>

            <button type="submit" style={{ width: 'fit-content' }}>
              Save Draft
            </button>
          </form>
        </div>

        <aside style={{ position: 'sticky', top: '20px' }}>
          <VoiceAssistantPanel />
        </aside>
      </div>
    </VoiceAssistantProvider>
  );
}
