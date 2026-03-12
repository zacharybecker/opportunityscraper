import { useState } from 'react'
import {
  Drawer, Stack, Title, Text, Badge, Group, Button, Textarea,
  Timeline, Divider, ActionIcon, Paper, Select, NumberInput,
} from '@mantine/core'
import { IconTrash, IconExternalLink } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import {
  getPipelineComments, addPipelineComment, deletePipelineComment,
  updatePipelineEntry, deletePipelineEntry,
} from '../../api'
import { notifications } from '@mantine/notifications'

const STAGES = [
  { value: 'found', label: 'Found' },
  { value: 'reviewing', label: 'Reviewing' },
  { value: 'pursuing', label: 'Pursuing' },
  { value: 'applied', label: 'Applied' },
  { value: 'won', label: 'Won' },
  { value: 'lost', label: 'Lost' },
  { value: 'archived', label: 'Archived' },
]

interface PipelineDetailDrawerProps {
  entry: any | null
  opened: boolean
  onClose: () => void
}

export default function PipelineDetailDrawer({ entry, opened, onClose }: PipelineDetailDrawerProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [commentText, setCommentText] = useState('')
  const [notes, setNotes] = useState('')
  const [editingNotes, setEditingNotes] = useState(false)

  const opp = entry?.opportunity

  const { data: comments } = useQuery({
    queryKey: ['pipeline-comments', entry?.id],
    queryFn: () => getPipelineComments(entry!.id),
    enabled: !!entry?.id,
  })

  const addCommentMutation = useMutation({
    mutationFn: () => addPipelineComment(entry!.id, commentText),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-comments', entry?.id] })
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
      setCommentText('')
    },
  })

  const deleteCommentMutation = useMutation({
    mutationFn: (commentId: string) => deletePipelineComment(entry!.id, commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-comments', entry?.id] })
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => updatePipelineEntry(entry!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
      notifications.show({ title: 'Updated', message: 'Entry updated', color: 'green' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deletePipelineEntry(entry!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
      onClose()
    },
  })

  if (!entry) return null

  return (
    <Drawer opened={opened} onClose={onClose} title="Pipeline Entry" position="right" size="lg">
      <Stack gap="md">
        <div>
          <Title order={4}>{opp?.title || 'Opportunity'}</Title>
          {opp?.solicitation_number && (
            <Text size="sm" c="dimmed">{opp.solicitation_number}</Text>
          )}
        </div>

        <Group gap="xs">
          {opp?.agency && <Badge variant="light">{opp.agency}</Badge>}
          {opp?.analysis?.relevancy_score != null && (
            <Badge
              color={
                opp.analysis.relevancy_score >= 70 ? 'green' :
                opp.analysis.relevancy_score >= 40 ? 'yellow' : 'red'
              }
            >
              {opp.analysis.relevancy_score}% relevant
            </Badge>
          )}
          {opp?.response_deadline && (
            <Badge color="orange">Due {dayjs(opp.response_deadline).format('MMM D, YYYY')}</Badge>
          )}
          {opp?.set_aside_type && <Badge variant="outline">{opp.set_aside_type}</Badge>}
        </Group>

        <Button
          variant="subtle" size="xs" leftSection={<IconExternalLink size={14} />}
          onClick={() => { onClose(); navigate(`/opportunities/${entry.opportunity_id}`) }}
        >
          View Full Opportunity
        </Button>

        <Divider />

        <Group grow>
          <Select
            label="Stage"
            data={STAGES}
            value={entry.stage}
            onChange={(val) => val && updateMutation.mutate({ stage: val })}
          />
          <NumberInput
            label="Priority"
            value={entry.priority}
            min={1} max={10}
            onChange={(val) => typeof val === 'number' && updateMutation.mutate({ priority: val })}
          />
        </Group>

        <div>
          <Group justify="space-between" mb={4}>
            <Text size="sm" fw={500}>Notes</Text>
            {!editingNotes && (
              <Button size="xs" variant="subtle" onClick={() => { setNotes(entry.notes || ''); setEditingNotes(true) }}>
                Edit
              </Button>
            )}
          </Group>
          {editingNotes ? (
            <Stack gap="xs">
              <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
              <Group gap="xs">
                <Button size="xs" onClick={() => { updateMutation.mutate({ notes }); setEditingNotes(false) }}>Save</Button>
                <Button size="xs" variant="subtle" onClick={() => setEditingNotes(false)}>Cancel</Button>
              </Group>
            </Stack>
          ) : (
            <Text size="sm" c={entry.notes ? undefined : 'dimmed'}>
              {entry.notes || 'No notes'}
            </Text>
          )}
        </div>

        <Divider />

        <div>
          <Text size="sm" fw={500} mb="xs">Stage History</Text>
          {entry.history?.length > 0 ? (
            <Timeline active={entry.history.length - 1} bulletSize={16} lineWidth={2}>
              {entry.history.map((h: any, i: number) => (
                <Timeline.Item key={i} title={`${h.from || 'Start'} → ${h.to}`}>
                  <Text size="xs" c="dimmed">
                    {h.notes && `${h.notes} · `}
                    {dayjs(h.at).format('MMM D, YYYY h:mm A')}
                  </Text>
                </Timeline.Item>
              ))}
            </Timeline>
          ) : (
            <Text size="sm" c="dimmed">No history</Text>
          )}
        </div>

        <Divider />

        <div>
          <Text size="sm" fw={500} mb="xs">Comments ({comments?.length || 0})</Text>
          <Stack gap="xs">
            {comments?.map((c: any) => (
              <Paper key={c.id} p="xs" radius="sm" bg="gray.0">
                <Group justify="space-between">
                  <Text size="sm">{c.content}</Text>
                  <ActionIcon size="xs" variant="subtle" color="red" onClick={() => deleteCommentMutation.mutate(c.id)}>
                    <IconTrash size={12} />
                  </ActionIcon>
                </Group>
                <Text size="xs" c="dimmed">{dayjs(c.created_at).format('MMM D, h:mm A')}</Text>
              </Paper>
            ))}
            <Group gap="xs">
              <Textarea
                placeholder="Add a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                style={{ flex: 1 }}
                rows={1}
              />
              <Button
                size="xs"
                onClick={() => addCommentMutation.mutate()}
                disabled={!commentText.trim()}
                loading={addCommentMutation.isPending}
              >
                Add
              </Button>
            </Group>
          </Stack>
        </div>

        <Divider />

        <Button color="red" variant="light" onClick={() => deleteMutation.mutate()} loading={deleteMutation.isPending}>
          Remove from Pipeline
        </Button>
      </Stack>
    </Drawer>
  )
}
