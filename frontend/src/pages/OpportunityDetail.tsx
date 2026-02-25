import {
  Title, Stack, Card, Group, Text, Badge, Button, Divider,
  Loader, Center, Grid, Progress, List, Accordion, Alert,
} from '@mantine/core'
import { IconArrowLeft, IconAnalyze, IconPlus, IconExternalLink, IconAlertCircle } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { getOpportunity, analyzeOpportunity, addToPipeline } from '../api'
import { notifications } from '@mantine/notifications'

export default function OpportunityDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: opp, isLoading } = useQuery({
    queryKey: ['opportunity', id],
    queryFn: () => getOpportunity(id!),
    enabled: !!id,
  })

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeOpportunity(id!),
    onSuccess: () => {
      notifications.show({ title: 'Analysis queued', message: 'AI analysis has been started', color: 'blue' })
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ['opportunity', id] }), 5000)
    },
  })

  const pipelineMutation = useMutation({
    mutationFn: () => addToPipeline({ opportunity_id: id! }),
    onSuccess: () => {
      notifications.show({ title: 'Added to pipeline', message: 'Opportunity added to pipeline', color: 'green' })
      queryClient.invalidateQueries({ queryKey: ['opportunity', id] })
    },
    onError: (err: any) => {
      notifications.show({ title: 'Error', message: err?.response?.data?.detail || 'Failed to add', color: 'red' })
    },
  })

  if (isLoading) return <Center h={400}><Loader /></Center>
  if (!opp) return <Text>Opportunity not found</Text>

  const analysis = opp.analysis
  const relevancyColor = (score: number) => {
    if (score >= 80) return 'green'
    if (score >= 50) return 'yellow'
    if (score >= 20) return 'orange'
    return 'red'
  }

  return (
    <Stack>
      <Group>
        <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={() => navigate(-1)}>
          Back
        </Button>
      </Group>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack>
          <Group justify="space-between" align="flex-start">
            <div style={{ flex: 1 }}>
              <Title order={3}>{opp.title}</Title>
              <Group mt="xs" gap="xs">
                {opp.solicitation_number && <Badge variant="light">{opp.solicitation_number}</Badge>}
                <Badge variant="light" color={opp.is_active ? 'green' : 'gray'}>
                  {opp.is_active ? 'Active' : 'Inactive'}
                </Badge>
                <Badge variant="light">{opp.source === 'sam_gov' ? 'SAM.gov' : opp.source}</Badge>
              </Group>
            </div>
            <Group>
              <Button
                leftSection={<IconAnalyze size={16} />}
                onClick={() => analyzeMutation.mutate()}
                loading={analyzeMutation.isPending}
                variant="light"
              >
                Analyze
              </Button>
              {!opp.pipeline_entry && (
                <Button
                  leftSection={<IconPlus size={16} />}
                  onClick={() => pipelineMutation.mutate()}
                  loading={pipelineMutation.isPending}
                >
                  Add to Pipeline
                </Button>
              )}
              {opp.pipeline_entry && (
                <Badge size="lg" color="blue">Pipeline: {opp.pipeline_entry.stage}</Badge>
              )}
            </Group>
          </Group>

          <Grid>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Stack gap="xs">
                <Text size="sm"><strong>Agency:</strong> {opp.agency || 'N/A'}</Text>
                <Text size="sm"><strong>Office:</strong> {opp.office || 'N/A'}</Text>
                <Text size="sm"><strong>NAICS:</strong> {opp.naics_code || 'N/A'}</Text>
                <Text size="sm"><strong>PSC:</strong> {opp.classification_code || 'N/A'}</Text>
                <Text size="sm"><strong>Set-Aside:</strong> {opp.set_aside_description || opp.set_aside_type || 'None'}</Text>
              </Stack>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Stack gap="xs">
                <Text size="sm"><strong>Posted:</strong> {opp.posted_date ? dayjs(opp.posted_date).format('MMM D, YYYY') : 'N/A'}</Text>
                <Text size="sm"><strong>Deadline:</strong> {opp.response_deadline ? dayjs(opp.response_deadline).format('MMM D, YYYY h:mm A') : 'N/A'}</Text>
                <Text size="sm"><strong>Location:</strong> {[opp.place_of_performance_city, opp.place_of_performance_state].filter(Boolean).join(', ') || 'N/A'}</Text>
                <Text size="sm"><strong>Contact:</strong> {opp.contact_name || 'N/A'} {opp.contact_email ? `(${opp.contact_email})` : ''}</Text>
                {opp.source_url && (
                  <Button
                    component="a"
                    href={opp.source_url}
                    target="_blank"
                    variant="light"
                    size="xs"
                    leftSection={<IconExternalLink size={14} />}
                  >
                    View Source
                  </Button>
                )}
              </Stack>
            </Grid.Col>
          </Grid>
        </Stack>
      </Card>

      {opp.description && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="sm">Description</Title>
          <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>{opp.description}</Text>
        </Card>
      )}

      {analysis && analysis.status === 'completed' && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="md">AI Analysis</Title>

          <Group mb="md">
            <div style={{ flex: 1 }}>
              <Text size="sm" c="dimmed">Relevancy Score</Text>
              <Group gap="xs">
                <Text fw={700} size="xl">{analysis.relevancy_score}%</Text>
                <Badge size="lg" color={relevancyColor(analysis.relevancy_score!)}>
                  {analysis.relevancy_label}
                </Badge>
              </Group>
              <Progress
                value={analysis.relevancy_score || 0}
                color={relevancyColor(analysis.relevancy_score!)}
                mt="xs"
                size="lg"
              />
            </div>
          </Group>

          {analysis.relevancy_explanation && (
            <Alert icon={<IconAlertCircle size={16} />} mb="md" variant="light">
              {analysis.relevancy_explanation}
            </Alert>
          )}

          <Accordion>
            {analysis.capability_matches?.length > 0 && (
              <Accordion.Item value="capabilities">
                <Accordion.Control>Capability Matches ({analysis.capability_matches.length})</Accordion.Control>
                <Accordion.Panel>
                  <List>
                    {analysis.capability_matches.map((m: any, i: number) => (
                      <List.Item key={i}>
                        <Text size="sm"><strong>{m.capability}</strong> ({m.match_strength}): {m.explanation}</Text>
                      </List.Item>
                    ))}
                  </List>
                </Accordion.Panel>
              </Accordion.Item>
            )}
            {analysis.gaps?.length > 0 && (
              <Accordion.Item value="gaps">
                <Accordion.Control>Gaps ({analysis.gaps.length})</Accordion.Control>
                <Accordion.Panel>
                  <List>
                    {analysis.gaps.map((g: any, i: number) => (
                      <List.Item key={i}>
                        <Text size="sm">
                          <Badge size="xs" color={g.severity === 'critical' ? 'red' : g.severity === 'moderate' ? 'yellow' : 'blue'} mr="xs">
                            {g.severity}
                          </Badge>
                          {g.description} — {g.recommendation}
                        </Text>
                      </List.Item>
                    ))}
                  </List>
                </Accordion.Panel>
              </Accordion.Item>
            )}
            {analysis.future_goal_matches?.length > 0 && (
              <Accordion.Item value="goals">
                <Accordion.Control>Future Goal Alignment ({analysis.future_goal_matches.length})</Accordion.Control>
                <Accordion.Panel>
                  <List>
                    {analysis.future_goal_matches.map((g: any, i: number) => (
                      <List.Item key={i}>
                        <Text size="sm"><strong>{g.goal_title}:</strong> {g.match_description}</Text>
                      </List.Item>
                    ))}
                  </List>
                </Accordion.Panel>
              </Accordion.Item>
            )}
          </Accordion>

          <Text size="xs" c="dimmed" mt="md">
            Analyzed {analysis.analyzed_at ? dayjs(analysis.analyzed_at).fromNow() : 'N/A'} using {analysis.ai_model} ({analysis.tokens_used} tokens)
          </Text>
        </Card>
      )}

      {analysis && analysis.status === 'pending' && (
        <Alert color="blue">Analysis is pending...</Alert>
      )}
      {analysis && analysis.status === 'running' && (
        <Alert color="yellow">Analysis is running...</Alert>
      )}
      {analysis && analysis.status === 'failed' && (
        <Alert color="red">Analysis failed: {analysis.error_message}</Alert>
      )}

      {opp.documents?.length > 0 && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="sm">Documents</Title>
          <List>
            {opp.documents.map((doc: any, i: number) => (
              <List.Item key={i}>
                <Group gap="xs">
                  <Text size="sm">{doc.filename}</Text>
                  <Badge size="xs">{doc.parse_status}</Badge>
                  {doc.url && (
                    <Button component="a" href={doc.url} target="_blank" variant="subtle" size="xs">
                      Download
                    </Button>
                  )}
                </Group>
              </List.Item>
            ))}
          </List>
        </Card>
      )}
    </Stack>
  )
}
