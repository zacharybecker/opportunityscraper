import { useState } from 'react'
import {
  Title, Stack, Text, Badge, Group, Loader, Center,
} from '@mantine/core'
import { DragDropContext, Droppable, type DropResult } from '@hello-pangea/dnd'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPipeline, movePipelineEntry } from '../api'
import PipelineCard from '../components/pipeline/PipelineCard'
import PipelineDetailDrawer from '../components/pipeline/PipelineDetailDrawer'

const STAGES = [
  { key: 'found', label: 'Found', color: 'gray' },
  { key: 'reviewing', label: 'Reviewing', color: 'blue' },
  { key: 'pursuing', label: 'Pursuing', color: 'cyan' },
  { key: 'applied', label: 'Applied', color: 'violet' },
  { key: 'won', label: 'Won', color: 'green' },
  { key: 'lost', label: 'Lost', color: 'red' },
  { key: 'archived', label: 'Archived', color: 'orange' },
]

export default function Pipeline() {
  const queryClient = useQueryClient()
  const [selectedEntry, setSelectedEntry] = useState<any>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['pipeline'],
    queryFn: getPipeline,
  })

  const moveMutation = useMutation({
    mutationFn: ({ id, stage, position }: { id: string; stage: string; position: number }) =>
      movePipelineEntry(id, { stage, position }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })

  const onDragEnd = (result: DropResult) => {
    const { draggableId, destination } = result
    if (!destination) return

    moveMutation.mutate({
      id: draggableId,
      stage: destination.droppableId,
      position: destination.index,
    })
  }

  if (isLoading) return <Center h={400}><Loader /></Center>

  return (
    <Stack>
      <Title order={2}>Pipeline</Title>

      <DragDropContext onDragEnd={onDragEnd}>
        <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 16 }}>
          {STAGES.map(({ key, label, color }) => {
            const entries: any[] = (data as any)?.[key] || []
            return (
              <div key={key} style={{ minWidth: 240, flex: 1 }}>
                <Group mb="xs" gap="xs">
                  <Badge color={color} size="lg">{label}</Badge>
                  <Badge variant="light" color="gray" size="sm">{entries.length}</Badge>
                </Group>
                <Droppable droppableId={key}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      style={{
                        minHeight: 100,
                        padding: 4,
                        borderRadius: 8,
                        backgroundColor: snapshot.isDraggingOver ? 'var(--mantine-color-blue-0)' : undefined,
                        transition: 'background-color 0.2s',
                      }}
                    >
                      <Stack gap="xs">
                        {entries.map((entry, index) => (
                          <PipelineCard
                            key={entry.id}
                            entry={entry}
                            index={index}
                            onClick={() => setSelectedEntry(entry)}
                          />
                        ))}
                        {provided.placeholder}
                        {entries.length === 0 && !snapshot.isDraggingOver && (
                          <Text size="sm" c="dimmed" ta="center" py="lg">Empty</Text>
                        )}
                      </Stack>
                    </div>
                  )}
                </Droppable>
              </div>
            )
          })}
        </div>
      </DragDropContext>

      <PipelineDetailDrawer
        entry={selectedEntry}
        opened={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
      />
    </Stack>
  )
}
